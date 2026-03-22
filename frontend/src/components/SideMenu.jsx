import { useNavigate, useLocation } from 'react-router-dom';

const NAV_ITEMS = [
  { path: '/', label: 'AI 文書校正', icon: '📝' },
  { path: '/history', label: '校正履歴', icon: '📋' },
  { path: null, label: '文書要約・翻訳', icon: '📄' },
  { path: null, label: 'PDF 加工', icon: '🗂' },
  { path: null, label: 'AI チャット', icon: '💬' },
];

const FOOTER_ITEMS = [
  { path: '/settings', label: '設定', icon: '⚙' },
];

function MenuItem({ path, label, icon, isActive }) {
  const navigate = useNavigate();
  const disabled = !path;

  const className = [
    'sidebar__item',
    isActive ? 'sidebar__item--active' : '',
    disabled ? 'sidebar__item--disabled' : '',
  ].filter(Boolean).join(' ');

  return (
    <button
      className={className}
      disabled={disabled}
      onClick={() => { if (path) navigate(path); }}
    >
      <span className="sidebar__item-icon">{icon}</span>
      {label}
    </button>
  );
}

function SideMenu() {
  const location = useLocation();

  return (
    <aside className="sidebar">
      <nav className="sidebar__nav">
        {NAV_ITEMS.map(item => (
          <MenuItem
            key={item.label}
            path={item.path}
            label={item.label}
            icon={item.icon}
            isActive={location.pathname === item.path}
          />
        ))}
      </nav>
      <div className="sidebar__footer">
        {FOOTER_ITEMS.map(item => (
          <MenuItem
            key={item.label}
            path={item.path}
            label={item.label}
            icon={item.icon}
            isActive={location.pathname === item.path}
          />
        ))}
      </div>
    </aside>
  );
}

export default SideMenu;
