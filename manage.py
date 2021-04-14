from flask_migrate import Migrate
from flask_migrate import MigrateCommand
from flask_script import Manager

from ros.lib.app import app, db
from seed import Seed

migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command("db", MigrateCommand)
manager.add_command('seed', Seed())

if __name__ == "__main__":
    manager.run()
