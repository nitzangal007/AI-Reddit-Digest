# app/formatter.py
# Beautiful response formatting for console output (English only)

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from typing import Optional
from .reddit_client import PostData

console = Console()


def print_markdown(text: str):
    """Print markdown-formatted text to console."""
    md = Markdown(text)
    console.print(md)


def print_panel(content: str, title: str = "", border_style: str = "blue"):
    """Print content in a styled panel."""
    console.print(Panel(
        Markdown(content),
        title=title,
        border_style=border_style,
        padding=(1, 2)
    ))


def print_welcome():
    """Print a beautiful welcome message."""
    title = "Reddit Digest - Smart Reddit Assistant"
    subtitle = "Ask me anything about what's happening on Reddit!"
    
    console.print()
    console.print(Panel(
        Text(subtitle, justify="center"),
        title=title,
        border_style="bright_blue",
        box=box.DOUBLE,
        padding=(1, 2)
    ))
    console.print()


def print_thinking():
    """Print a thinking indicator."""
    console.print("\n[dim italic]Searching and processing...[/dim italic]\n")


def print_response(response: str, title: Optional[str] = None):
    """Print an AI response in a styled panel."""
    panel_title = title or "Response"
    
    console.print()
    console.print(Panel(
        Markdown(response),
        title=panel_title,
        border_style="green",
        padding=(1, 2)
    ))
    console.print()


def print_error(message: str):
    """Print an error message."""
    console.print(f"\n[bold red]Error:[/bold red] {message}\n")


def print_info(message: str):
    """Print an info message."""
    console.print(f"[dim]Info: {message}[/dim]")


def print_success(message: str):
    """Print a success message."""
    console.print(f"[bold green]Success:[/bold green] {message}")


def print_warning(message: str):
    """Print a warning message."""
    console.print(f"[bold yellow]Warning:[/bold yellow] {message}")


def print_posts_table(posts: list[PostData]):
    """Print posts in a formatted table."""
    if not posts:
        print_warning("No posts found")
        return
    
    table = Table(
        title="Posts Found",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("#", style="dim", width=3)
    table.add_column("Title", style="white", max_width=50)
    table.add_column("Score", justify="right", style="green")
    table.add_column("Comments", justify="right", style="yellow")
    
    for i, post in enumerate(posts, 1):
        title = post.get('title', 'No title')
        if len(title) > 47:
            title = title[:47] + "..."
        
        table.add_row(
            str(i),
            title,
            str(post.get('score', 0)),
            str(post.get('num_comments', 0))
        )
    
    console.print()
    console.print(table)
    console.print()


def format_post_detail(post: PostData) -> str:
    """Format a single post for detailed display."""
    lines = []
    
    lines.append(f"### {post.get('title', 'No title')}")
    lines.append("")
    lines.append(f"**{post.get('score', 0)}** points | **{post.get('num_comments', 0)}** comments")
    lines.append(f"[Link]({post.get('permalink', '#')})")
    lines.append("")
    
    selftext = post.get('selftext', '')
    if selftext:
        if len(selftext) > 500:
            selftext = selftext[:500] + "..."
        lines.append(f"> {selftext}")
        lines.append("")
    
    return "\n".join(lines)


def print_divider():
    """Print a visual divider."""
    console.print("-" * 60, style="dim")


def print_prompt():
    """Print the input prompt."""
    console.print("\n[bold cyan]You:[/bold cyan] ", end="")


def get_user_input() -> str:
    """Get user input with a styled prompt."""
    print_prompt()
    try:
        return input().strip()
    except (KeyboardInterrupt, EOFError):
        return "/quit"


def print_goodbye():
    """Print a goodbye message."""
    console.print()
    console.print(Panel(
        Text("Goodbye! Thanks for using Reddit Digest", justify="center"),
        border_style="bright_blue",
        padding=(1, 2)
    ))
    console.print()
