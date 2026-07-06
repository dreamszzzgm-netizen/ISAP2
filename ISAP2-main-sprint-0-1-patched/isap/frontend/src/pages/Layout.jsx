import React from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const navGroups = [
  {
    title: 'Основное',
    items: [
      { to: '/', label: 'Дашборд', icon: 'fas fa-chart-pie' },
      { to: '/pmla', label: 'Генерация ПМЛА', icon: 'fas fa-file-shield' },
      { to: '/documents', label: 'Документы', icon: 'fas fa-folder-open' },
    ],
  },
  {
    title: 'Справочники',
    items: [
      { to: '/organizations', label: 'Организации', icon: 'fas fa-building' },
      { to: '/facilities', label: 'Объекты ОПО', icon: 'fas fa-industry' },
      { to: '/persons', label: 'Ответственные лица', icon: 'fas fa-users' },
    ],
  },
  {
    title: 'Система',
    items: [
      { to: '/regulatory', label: 'Нормативы', icon: 'fas fa-book' },
      { to: '/samples', label: 'Образцы ПМЛА', icon: 'fas fa-file-alt' },
      { to: '/ai', label: 'AI / LM Studio', icon: 'fas fa-brain' },
    ],
  },
];

const pageTitles = {
  '/': 'Дашборд',
  '/pmla': 'Генерация ПМЛА',
  '/documents': 'Документы',
  '/organizations': 'Организации',
  '/facilities': 'Объекты ОПО',
  '/persons': 'Ответственные лица',
  '/regulatory': 'Нормативы',
  '/samples': 'Образцы ПМЛА',
  '/ai': 'AI / LM Studio',
};

export default function Layout() {
  const location = useLocation();
  const basePath = '/' + (location.pathname.split('/')[1] || '');
  const pageTitle = pageTitles[basePath] || 'ИСАП';
  const { logout } = useAuth();

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <aside className="sidebar">
        <div className="sidebar-header">
          <NavLink to="/" className="logo">
            <i className="fas fa-shield-alt"></i>
            <span>ИСАП ПМЛА</span>
          </NavLink>
        </div>
        <nav className="sidebar-nav">
          {navGroups.map((group) => (
            <div key={group.title} className="nav-section">
              <div className="nav-section-title">{group.title}</div>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
                  className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
                >
                  <i className={item.icon}></i>
                  <span>{item.label}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="user-card" onClick={logout} style={{ cursor: 'pointer' }} title="Выйти">
            <div className="user-avatar">
              <i className="fas fa-sign-out-alt" style={{ fontSize: 14 }}></i>
            </div>
            <div className="user-info">
              <div className="user-name">Выйти</div>
              <div className="user-role">Завершить сессию</div>
            </div>
          </div>
        </div>
      </aside>

      <div className="main">
        <header className="header">
          <div className="header-left">
            <h1 className="header-title">{pageTitle}</h1>
          </div>
          <div className="header-right">
            <div className="search-box">
              <i className="fas fa-search"></i>
              <input type="text" placeholder="Поиск по ПМЛА, объектам, нормативам..." />
            </div>
            <button className="header-btn">
              <i className="fas fa-bell"></i>
            </button>
            <button className="header-btn">
              <i className="fas fa-question-circle"></i>
            </button>
          </div>
        </header>
        <div className="content">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
