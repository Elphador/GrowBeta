from rich.text import Text
from typing import Dict, Optional, List
import time
from datetime import datetime
import asyncio
import aiohttp
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.style import Style
from rich.layout import Layout
from rich.live import Live

console = Console()

class FollowerBot:
    def __init__(self, domain: str, color: str):
        self.domain = domain
        self.color = color
        self.session = None
        self.is_logged_in = False
        self.base_url = f"https://{domain}"
        self.headers = {
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': self.base_url,
            'priority': 'u=1, i',
            'referer': f'{self.base_url}/login',
            'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        }
        
        if domain == 'fastfollow.in':
            self.login_url = f"{self.base_url}/member?"
            self.cookies = {
                '_ga': 'GA1.2.1922977131.1750655906',
                '_gid': 'GA1.2.525458018.1750655906',
                'd9db20899806730bac338dcdc8dd11ab': 'db1240212802405996e7f635cfea8d0a',
            }
        else:
            self.login_url = f"{self.base_url}/login?"
            self.cookies = {
                '169c233b09368cc79f28663114c55175': 'b559f22c55d5781225770d491be547cd',
                '_ga': 'GA1.2.185552074.1750652301',
                '_gid': 'GA1.2.108600278.1750652301',
                'fpestid': 'viWY8GCkFFGNf9XZZthktmM3Axdzaoysfw3j1EDlG_22dAIq5rFuq5SEo1GzlVWENctBYQ',
            }

    async def update_display(self, live: Live, message: str):
        live.update(Panel(message))
        await asyncio.sleep(0.1)

    async def login(self, username: str, password: str, live: Live) -> bool:
        try:
            data = {
                'username': username,
                'password': password,
                'userid': '',
                'antiForgeryToken': '3f1887e6c0c9575f7072e0ea39fa9c55' if self.domain == 'fastfollow.in' else '31b937a91142113ba83258c654f817a4'
            }
            
            await self.update_display(live, f"[{self.domain.upper()}] Logging in...")
            async with self.session.post(self.login_url, data=data) as response:
                if response.status != 200:
                    await self.update_display(live, f"[{self.domain.upper()}] [red]Login failed with status {response.status}[/red]")
                    return False
                
                self.session.cookie_jar.update_cookies(response.cookies)
                self.is_logged_in = True
                await self.update_display(live, f"[{self.domain.upper()}] [green]Login successful![/green]")
                return True
                
        except Exception as e:
            await self.update_display(live, f"[{self.domain.upper()}] [red]Login error: {str(e)}[/red]")
            return False

    async def check_session(self, live: Live) -> bool:
        if not self.is_logged_in:
            return False
            
        try:
            url = f"{self.base_url}/ajax/keep-session"
            async with self.session.get(url) as response:
                if response.status == 200:
                    return True
                
            await self.update_display(live, f"[{self.domain.upper()}] [yellow]Session might be expired, trying to refresh...[/yellow]")
            async with self.session.get(url) as response:
                if response.status == 200:
                    return True
                
            return False
                
        except Exception as e:
            await self.update_display(live, f"[{self.domain.upper()}] [red]Session check error: {str(e)}[/red]")
            return False

    async def ensure_session(self, username: str, password: str, live: Live) -> bool:
        if self.is_logged_in:
            if await self.check_session(live):
                await self.update_display(live, f"[{self.domain.upper()}] [green]Using existing session[/green]")
                return True
            else:
                await self.update_display(live, f"[{self.domain.upper()}] [yellow]Session expired, re-logging in...[/yellow]")
                self.is_logged_in = False
                
        return await self.login(username, password, live)

    async def find_user_id(self, username: str, live: Live) -> Optional[str]:
        try:
            url = f"{self.base_url}/tools/send-follower"
            params = {'formType': 'findUserID'}
            data = {'username': username}
            
            await self.update_display(live, f"[{self.domain.upper()}] Finding user ID...")
            async with self.session.post(url, params=params, data=data) as response:
                if response.status != 200:
                    await self.update_display(live, f"[{self.domain.upper()}] [red]Find user ID failed with status {response.status}[/red]")
                    return None
                
                final_url = str(response.url)
                user_id = final_url.split('/')[-1]
                
                if not user_id.isdigit():
                    await self.update_display(live, f"[{self.domain.upper()}] [red]Invalid user ID received[/red]")
                    return None
                
                await self.update_display(live, f"[{self.domain.upper()}] [green]Found user ID: {user_id}[/green]")
                return user_id
                
        except Exception as e:
            await self.update_display(live, f"[{self.domain.upper()}] [red]Find user ID error: {str(e)}[/red]")
            return None

    async def send_followers(self, user_id: str, username: str, count: str, live: Live) -> bool:
        try:
            url = f"{self.base_url}/tools/send-follower/{user_id}"
            params = {'formType': 'send'}
            data = {
                'adet': count,
                'userID': user_id,
                'userName': username
            }
            
            await self.update_display(live, f"[{self.domain.upper()}] Sending {count} followers...")
            async with self.session.post(url, params=params, data=data) as response:
                if response.status != 200:
                    await self.update_display(live, f"[{self.domain.upper()}] [red]Send followers failed with status {response.status}[/red]")
                    return False
                
                result = await response.text()
                await self.update_display(live, f"[{self.domain.upper()}] [green]Followers sent successfully![/green]\nResponse: {result}")
                return True
                
        except Exception as e:
            await self.update_display(live, f"[{self.domain.upper()}] [red]Send followers error: {str(e)}[/red]")
            return False

    async def run_operations(self, credentials: Dict, target: Dict, live: Live):
        try:
            self.session = aiohttp.ClientSession(headers=self.headers, cookies=self.cookies)
            
            if not await self.ensure_session(credentials['username'], credentials['password'], live):
                await self.update_display(live, f"[{self.domain.upper()}] [red]Session initialization failed. Skipping...[/red]")
                return
                
            user_id = await self.find_user_id(target['username'], live)
            if not user_id:
                await self.update_display(live, f"[{self.domain.upper()}] [red]Failed to find user ID. Skipping...[/red]")
                return
                
            if not await self.send_followers(user_id, target['username'], target['count'], live):
                await self.update_display(live, f"[{self.domain.upper()}] [red]Failed to send followers. Skipping...[/red]")
                return
                
            await self.update_display(live, f"[{self.domain.upper()}] [green]Operation completed successfully![/green]")
            
        except Exception as e:
            await self.update_display(live, f"[{self.domain.upper()}] [red]Unexpected error: {str(e)}[/red]")
        finally:
            if self.session:
                await self.session.close()

def display_banner():
    banner = Text("""
        ██████╗ ██████╗  ██████╗ ██╗    ██╗██████╗ ███████╗████████╗ █████╗ 
        ██╔══██╗██╔══██╗██╔═══██╗██║    ██║██╔══██╗██╔════╝╚══██╔══╝██╔══██╗
        ██║  ██║██████╔╝██║   ██║██║ █╗ ██║██████╔╝█████╗     ██║   ███████║
        ██║  ██║██╔══██╗██║   ██║██║███╗██║██╔══██╗██╔══╝     ██║   ██╔══██║
        ██████╔╝██║  ██║╚██████╔╝╚███╔███╔╝██████╔╝███████╗   ██║   ██║  ██║
        ╚═════╝ ╚═╝  ╚═╝ ╚═════╝  ╚══╝╚══╝ ╚═════╝ ╚══════╝   ╚═╝   ╚═╝  ╚═╝
        """, style="bold magenta")
    
    subtitle = Text("Instagram Followers Adder - Powered by elphador | Deployable", style="bold blue")
    
    console.print(Panel(banner, subtitle=subtitle, border_style="green", width=80))
    console.print()

def get_user_input():
    accounts = []
    
    console.print("[bold yellow]Enter account credentials (leave username empty to finish):[/bold yellow]")
    while True:
        username = console.input("[bold blue]>> Username: [/bold blue]").strip()
        if not username:
            break
        password = console.input("[bold blue]>> Password: [/bold blue]", password=True).strip()
        accounts.append({'username': username, 'password': password})
    
    if not accounts:
        console.print("[bold red]No accounts provided! Exiting...[/bold red]")
        exit()
    
    table = Table(title="[bold green]Accounts to Process[/bold green]", show_header=True, header_style="bold magenta")
    table.add_column("Username", style="cyan")
    table.add_column("Password", style="cyan")
    for acc in accounts:
        table.add_row(acc['username'], "*" * len(acc['password']))
    console.print(table)
    
    target_username = console.input("[bold blue]>> Target Username: [/bold blue]").strip()
    followers_count = console.input("[bold blue]>> Followers to Send (default 50): [/bold blue]").strip() or "50"
    interval = console.input("[bold blue]>> Interval in minutes (default 10): [/bold blue]").strip() or "10"
    
    return {
        'accounts': accounts,
        'target': {
            'username': target_username,
            'count': followers_count
        },
        'interval': int(interval) * 60  # Convert to seconds
    }

async def main_loop():
    display_banner()
    config = get_user_input()
    
    while True:
        start_time = time.time()
        
        bots = [
            FollowerBot('takipstar.com', "cyan"),
            FollowerBot('takipcigir.com', "yellow"),
            FollowerBot('fastfollow.in', "magenta")
        ]
        
        for account in config['accounts']:
            with Live(Panel(f"[bold green]Processing account: {account['username']}[/bold green]"), refresh_per_second=4) as live:
                tasks = [bot.run_operations(account, config['target'], live) for bot in bots]
                await asyncio.gather(*tasks)
                
                await asyncio.sleep(1)
        
        elapsed = time.time() - start_time
        sleep_time = max(0, config['interval'] - elapsed)
        
        if sleep_time > 0:
            with Live() as live:
                remaining = sleep_time
                while remaining > 0:
                    mins, secs = divmod(remaining, 60)
                    live.update(Panel(f"[bold blue]Next run in: {int(mins):02d}:{int(secs):02d}[/bold blue]"))
                    await asyncio.sleep(1)
                    remaining -= 1
        
        console.print("[bold green]Restarting process...[/bold green]")

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        console.print("[bold red]Script terminated by user![/bold red]")
    except Exception as e:
        console.print(f"[bold red]Fatal error: {str(e)}[/bold red]")