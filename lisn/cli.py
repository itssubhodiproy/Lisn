"""
CLI entry point for Lisn.

Commands:
  lisn setup   - Configure Lisn (API key, settings)
  lisn status  - Show current status and configuration
  lisn start   - Start the dictation daemon
  lisn stop    - Stop the dictation daemon
"""

import click

from lisn import __version__
from lisn.config import Config


@click.group()
@click.version_option(version=__version__, prog_name="lisn")
def main():
    """Lisn - Push-to-talk voice dictation for Linux.
    
    Hold CapsLock to record, release to transcribe.
    Uses Groq Cloud (Whisper + LLM) for fast, accurate dictation.
    """
    pass


@main.command()
@click.option("--api-key", prompt="Groq API Key", hide_input=True,
              help="Your Groq API key (get one at console.groq.com)")
def setup(api_key: str):
    """Configure Lisn with your API key and preferences."""
    config = Config.load()
    config.api.api_key = api_key
    config.save()
    
    click.echo(click.style("✓ ", fg="green") + "Configuration saved!")
    click.echo(f"  Config file: {Config.get_config_path()}")
    click.echo()
    click.echo("You can now start Lisn with: " + click.style("lisn start", bold=True))


@main.command()
def status():
    """Show current status and configuration."""
    from lisn.process import get_status
    
    config = Config.load()
    errors = config.validate()
    daemon_status = get_status()
    
    click.echo(click.style("Lisn Status", bold=True))
    click.echo("─" * 30)
    
    # Config status
    click.echo(f"Config: {Config.get_config_path()}")
    
    # API status
    if config.api.api_key:
        masked_key = config.api.api_key[:8] + "..." + config.api.api_key[-4:]
        click.echo(f"API Key: {masked_key}")
    else:
        click.echo(click.style("API Key: Not set", fg="yellow"))
    
    click.echo(f"Whisper Model: {config.api.whisper_model}")
    click.echo(f"LLM Model: {config.api.llm_model}")
    click.echo()
    
    # Audio settings
    click.echo(f"Audio: {config.audio.sample_rate}Hz, {config.audio.channels}ch")
    click.echo(f"Hotkey: {config.hotkey.trigger}")
    click.echo()
    
    # Validation
    if errors:
        click.echo(click.style("Issues:", fg="yellow"))
        for error in errors:
            click.echo(f"  ⚠ {error}")
    else:
        click.echo(click.style("✓ Ready to use", fg="green"))
    
    # Daemon status
    click.echo()
    if daemon_status["running"]:
        click.echo("Daemon: " + click.style(f"Running (PID {daemon_status['pid']})", fg="green"))
    else:
        click.echo("Daemon: " + click.style("Not running", fg="yellow"))


@main.command()
@click.option("--foreground", "-f", is_flag=True, help="Run in foreground (don't daemonize)")
def start(foreground: bool):
    """Start the dictation daemon."""
    from lisn.process import start_daemon, is_running
    
    config = Config.load()
    errors = config.validate()
    
    if errors:
        click.echo(click.style("Cannot start - configuration issues:", fg="red"))
        for error in errors:
            click.echo(f"  ⚠ {error}")
        raise SystemExit(1)
    
    if is_running():
        click.echo(click.style("Lisn is already running", fg="yellow"))
        click.echo("Use 'lisn stop' to stop, or 'lisn restart' to restart")
        raise SystemExit(1)
    
    if foreground:
        click.echo(click.style("Starting Lisn in foreground...", fg="green"))
        click.echo("Press Ctrl+C to stop")
        click.echo()
    
    start_daemon(foreground=foreground)


@main.command()
def stop():
    """Stop the dictation daemon."""
    from lisn.process import stop_daemon
    stop_daemon()


@main.command()
def restart():
    """Restart the dictation daemon."""
    from lisn.process import restart_daemon
    restart_daemon()


if __name__ == "__main__":
    main()

