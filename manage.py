from ros.lib.app import app
import click
from flask.cli import with_appcontext
from seed import Seed


@click.command(name='seed')
@with_appcontext
def seed():
    Seed().run()


app.cli.add_command(seed)
