import os


class Config:
    def __init__(self):
        self.db_user = os.getenv("ROS_DB_USER", "postgres")
        self.db_password = os.getenv("ROS_DB_PASS", "postgres")
        self.db_host = os.getenv("ROS_DB_HOST", "localhost")
        self.db_port = os.getenv("ROS_DB_PORT", "15432")
        self.db_name = os.getenv("ROS_DB_NAME", "postgres")
        self.db_uri = f"postgresql://{self.db_user}:{self.db_password}"\
                      f"@{self.db_host}:{self.db_port}/{self.db_name}"
