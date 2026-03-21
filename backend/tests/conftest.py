import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def db_engine():
    """インメモリ SQLite エンジン（テスト用）"""
    engine = create_engine("sqlite:///:memory:")
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """テスト用 DB セッション。テストごとにロールバック。

    begin_nested() セーブポイントパターンを使用することで、
    テスト内で session.commit() を呼んでも外側のトランザクションで
    ロールバックされ、テスト間のデータ汚染を防ぐ。
    """
    from database import Base
    Base.metadata.create_all(db_engine)
    connection = db_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    session.begin_nested()

    # セーブポイントが終了したら新しいセーブポイントを開始
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    yield session
    session.close()
    transaction.rollback()
    connection.close()
