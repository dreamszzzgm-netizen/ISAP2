import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const [key, setKey] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const API_BASE = import.meta.env.VITE_API_URL || '';
      const response = await fetch(`${API_BASE}/api/v1/organizations/`, {
        headers: { 'Authorization': `Bearer ${key}` },
      });

      if (response.ok) {
        login(key);
      } else if (response.status === 401) {
        const data = await response.json().catch(() => ({}));
        setError(data.detail || 'Неверный ключ доступа');
      } else {
        setError(`Ошибка сервера: ${response.status}`);
      }
    } catch {
      setError('Не удалось подключиться к серверу');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-header">
          <div className="login-icon">
            <i className="fas fa-shield-alt"></i>
          </div>
          <h1 className="login-title">ИСАП ПМЛА</h1>
          <p className="login-subtitle">Промышленная безопасность</p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Ключ доступа</label>
            <input
              type="password"
              className="form-input"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              placeholder="Введите ключ доступа"
              autoFocus
            />
          </div>

          {error && (
            <div className="alert alert-error">{error}</div>
          )}

          <button
            type="submit"
            className={`btn login-btn ${key.trim() ? 'btn-primary' : ''}`}
            disabled={!key.trim() || loading}
          >
            {loading ? 'Проверка...' : 'Войти'}
          </button>
        </form>
      </div>
    </div>
  );
}
