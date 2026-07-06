import React, { useState, useEffect } from 'react';
import { organizationsApi } from '../api';

const emptyForm = { name: '', inn: '', ogrn: '', address: '', phone: '', email: '' };

export default function Organizations() {
  const [orgs, setOrgs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true);
    try { setOrgs(await organizationsApi.list()); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const handleSubmit = async () => {
    if (!form.name.trim() || !form.inn.trim()) return;
    setError(null);
    try {
      const data = {};
      Object.entries(form).forEach(([k, v]) => { data[k] = v || null; });
      if (editingId) { await organizationsApi.update(editingId, data); }
      else { await organizationsApi.create(data); }
      setForm(emptyForm); setEditingId(null); setShowForm(false);
      await load();
    } catch (e) { setError(e.message); }
  };

  const handleEdit = (org) => {
    setEditingId(org.id);
    setForm({ name: org.name, inn: org.inn, ogrn: org.ogrn || '', address: org.address || '', phone: org.phone || '', email: org.email || '' });
    setShowForm(true);
  };

  const handleDelete = async (id) => {
    if (!confirm('Удалить организацию?')) return;
    try { await organizationsApi.delete(id); await load(); }
    catch (e) { setError(e.message); }
  };

  const resetForm = () => { setForm(emptyForm); setEditingId(null); setShowForm(false); };
  const handleChange = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  return (
    <div>
      <div className="section">
        <div className="section-header">
          <div className="section-title">Организации</div>
          <div className="section-actions">
            {!showForm && (
              <button className="btn btn-primary btn-sm" onClick={() => { resetForm(); setShowForm(true); }}>
                <i className="fas fa-plus"></i> Добавить
              </button>
            )}
          </div>
        </div>

        {showForm && (
          <div style={{ padding: 24, borderBottom: '1px solid var(--gray-100)', background: 'var(--gray-50)' }}>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: 'var(--gray-700)' }}>
              {editingId ? 'Редактирование' : 'Новая организация'}
            </div>
            <div className="form-grid">
              <div className="form-group">
                <label className="form-label">Наименование <span className="required">*</span></label>
                <input className="form-input" value={form.name} onChange={handleChange('name')} />
              </div>
              <div className="form-group">
                <label className="form-label">ИНН <span className="required">*</span></label>
                <input className="form-input" value={form.inn} onChange={handleChange('inn')} />
              </div>
              <div className="form-group">
                <label className="form-label">ОГРН</label>
                <input className="form-input" value={form.ogrn} onChange={handleChange('ogrn')} />
              </div>
              <div className="form-group">
                <label className="form-label">Адрес</label>
                <input className="form-input" value={form.address} onChange={handleChange('address')} />
              </div>
              <div className="form-group">
                <label className="form-label">Телефон</label>
                <input className="form-input" value={form.phone} onChange={handleChange('phone')} />
              </div>
              <div className="form-group">
                <label className="form-label">Email</label>
                <input className="form-input" value={form.email} onChange={handleChange('email')} />
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
              <button className="btn btn-primary btn-sm" onClick={handleSubmit}>{editingId ? 'Сохранить' : 'Создать'}</button>
              <button className="btn btn-secondary btn-sm" onClick={resetForm}>Отмена</button>
            </div>
          </div>
        )}

        {error && <div style={{ padding: '12px 24px', background: 'var(--danger-light)', color: 'var(--danger)', fontSize: 13 }}>{error}</div>}

        {loading ? (
          <div className="loading-center"><div className="spinner"></div></div>
        ) : orgs.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--gray-400)' }}>Нет организаций</div>
        ) : (
          <table className="data-table">
            <thead><tr><th>Наименование</th><th>ИНН</th><th>Адрес</th><th>Телефон</th><th></th></tr></thead>
            <tbody>
              {orgs.map(org => (
                <tr key={org.id}>
                  <td><strong>{org.name}</strong></td>
                  <td>{org.inn}</td>
                  <td>{org.address || '—'}</td>
                  <td>{org.phone || '—'}</td>
                  <td>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button className="btn btn-ghost btn-sm" onClick={() => handleEdit(org)}><i className="fas fa-edit"></i></button>
                      <button className="btn btn-ghost btn-sm" style={{ color: 'var(--danger)' }} onClick={() => handleDelete(org.id)}><i className="fas fa-trash"></i></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
