function App() {
  return (
    <div className="app">
      <header className="app-header">
        <span className="app-header__title">GovAssist</span>
        <div className="app-header__actions">
          <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
            Task 13 で実装
          </span>
        </div>
      </header>
      <div className="app-content">
        <aside className="sidebar">
          <nav className="sidebar__nav">
            <button className="sidebar__item sidebar__item--active">
              <span className="sidebar__item-icon">📝</span>
              AI 文書校正
            </button>
            <button className="sidebar__item sidebar__item--disabled">
              <span className="sidebar__item-icon">📄</span>
              文書要約・翻訳
            </button>
            <button className="sidebar__item sidebar__item--disabled">
              <span className="sidebar__item-icon">🗂</span>
              PDF 加工
            </button>
            <button className="sidebar__item sidebar__item--disabled">
              <span className="sidebar__item-icon">💬</span>
              AI チャット
            </button>
          </nav>
          <div className="sidebar__footer">
            <button className="sidebar__item">
              <span className="sidebar__item-icon">⚙</span>
              設定
            </button>
          </div>
        </aside>
        <main className="main-content">
          <div className="card">
            <h2 style={{ marginBottom: 'var(--spacing-sm)' }}>GovAssist へようこそ</h2>
            <p style={{ color: 'var(--color-text-secondary)' }}>
              フロントエンドプロジェクトセットアップ完了（Task 12）
            </p>
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
