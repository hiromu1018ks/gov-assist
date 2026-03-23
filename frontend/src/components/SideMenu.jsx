import { useNavigate, useLocation } from 'react-router-dom';

const NAV_ITEMS = [
  { path: '/', label: 'proofread', displayLabel: '校正ツール', icon: '○' },
  { path: '/history', label: 'history', displayLabel: '履歴', icon: '○' },
  { path: null, label: 'translate', displayLabel: '翻訳ツール', icon: '○' },
  { path: null, label: 'summarize', displayLabel: '要約ツール', icon: '○' },
  { path: null, label: 'format', displayLabel: 'フォーマット', icon: '○' },
];

const FOOTER_ITEMS = [
  { path: '/settings', label: 'settings', displayLabel: '設定', icon: '○' },
];

function MenuItem({ path, label, displayLabel, icon, isActive }) {
  const navigate = useNavigate();
  const disabled = !path;
  const activeIcon = isActive ? '▸' : icon;

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
      <span className="sidebar__item-icon">{activeIcon}</span>
      {displayLabel}
    </button>
  );
}

function SideMenu() {
  const location = useLocation();

  return (
    <aside className="sidebar">
      <div className="sidebar__label">[ MODULES ]</div>
      <nav className="sidebar__nav">
        {NAV_ITEMS.map(item => (
          <MenuItem
            key={item.label}
            path={item.path}
            label={item.label}
            displayLabel={item.displayLabel}
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
            displayLabel={item.displayLabel}
            icon={item.icon}
            isActive={location.pathname === item.path}
          />
        ))}
      </div>
    </aside>
  );
}

export default SideMenu;
