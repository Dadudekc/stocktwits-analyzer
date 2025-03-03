from unittest.mock import MagicMock
import mysql.connector

# Patch mysql.connector.connect to return a dummy connection object.
mysql.connector.connect = MagicMock(return_value=MagicMock(
    cursor=lambda: MagicMock(),
    commit=lambda: None,
    rollback=lambda: None,
    close=lambda: None
))
