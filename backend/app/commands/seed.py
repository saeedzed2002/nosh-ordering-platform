from alembic.config import Config
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import get_settings
from app.db.session import get_engine
from app.services.seed import seed_database


def main() -> None:
    settings = get_settings()
    alembic_config = Config("alembic.ini")
    command.upgrade(alembic_config, "head")
    with Session(get_engine(settings.database_url)) as session:
        seed_database(session, settings)


if __name__ == "__main__":
    main()
