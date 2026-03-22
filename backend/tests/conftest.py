import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def db_engine():
    """インメモリ SQLite エンジン（テスト用）"""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
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
    import models  # noqa: F401 — register ORM models with Base.metadata
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


@pytest.fixture
def app_client(db_session):
    """認証付き TestClient。DB セッションを注入する。"""
    from fastapi.testclient import TestClient
    from main import create_app
    # from dependencies import get_app_token  # Auth disabled for localhost MVP
    from database import get_db

    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # セッションは db_session フィクスチャで管理

    app = create_app(enable_origin_check=False)
    # app.dependency_overrides[get_app_token] = lambda: "test-secret-token"  # Auth disabled
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
