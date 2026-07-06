import React, { useState, useEffect } from 'react';
import { personsApi, organizationsApi } from '../api';
import { roleLabel, orgName as orgNameUtil } from '../constants';

const emptyForm = { organization_id: '', full_name: '', position: '', role: '', phone: '', email: '' };

export default function Persons() {
  const [persons, setPersons] = useState([]);
  const [organizations, setOrganizations] = useState([]);
  const [selectedOrg, setSelectedOrg] = useState('');
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const [orgs, ps] = await Promise.all([
        organizationsApi.list(),
        personsApi.list(selectedOrg || null),
      ]);
      setOrganizations(orgs);
      setPersons(ps);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [selectedOrg]);

  const resetForm = () => { setForm(emptyForm); setEditingId(null); setShowForm(false); };

  const handleSubmit = async () => {
    if (!form.full_name.trim() || !form.organization_id) return;
    setError(null);
    try {
      const data = {};
      Object.entries(form).forEach(([k, v]) => { data[k] = v || null; });
      if (editingId) { await personsApi.update(editingId, data); }
      else { await personsApi.create(data); }
      resetForm();
      await load();
    } catch (e) { setError(e.message); }
  };

  const handleEdit = (p) => {
    setEditingId(p.id);
    setForm({
      organization_id: p.organization_id, full_name: p.full_name,
      position: p.position || '', role: p.role || '', phone: p.phone || '', email: p.email || '',
    });
    setShowForm(true);
  };

  const handleDelete = async (pid) => {
    if (!confirm('Удалить запись?')) return;
    try { await personsApi.delete(pid); await load(); } catch (e) { setError(e.message); }
  };

  const orgName = (id) => orgNameUtil(organizations, id);
  const handleChange = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  return (
    <div>
      <div className="section">
        <div className="section-header">
          <div className="section-title">Ответственные лица</div>
          <div className="section-actions">
            {!showForm && (
              <button className="btn btn-primary btn-sm" onClick={() => { resetForm(); setShowForm(true); }}>
                <i className="fas fa-plus"></i> Добавить
              </button>
            )}
          </div>
        </div>

        <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--gray-100)' }}>
          <div className="form-group" style={{ maxWidth: 300 }}>
            <select className="form-select" value={selectedOrg} onChange={e => setSelectedOrg(e.target.value)}>
              <option value="">Все организации</option>
              {organizations.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
            </select>
          </div>
        </div>

        {showForm && (
          <div style={{ padding: 24, borderBottom: '1px solid var(--gray-100)', background: 'var(--gray-50)' }}>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: 'var(--gray-700)' }}>
              {editingId ? 'Редактирование' : 'Новое лицо'}
            </div>
            <div className="form-grid">
              <div className="form-group">
                <label className="form-label">Организация <span className="required">*</span></label>
                <select className="form-select" value={form.organization_id} onChange={handleChange('organization_id')}>
                  <option value="">— Выберите —</option>
                  {organizations.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">ФИО <span className="required">*</span></label>
                <input className="form-input" value={form.full_name} onChange={handleChange('full_name')} />
              </div>
              <div className="form-group">
                <label className="form-label">Должность</label>
                <input className="form-input" value={form.position} onChange={handleChange('position')} />
              </div>
              <div className="form-group">
                <label className="form-label">Роль</label>
                <select className="form-select" value={form.role} onChange={handleChange('role')}>
                  <option value="">— Не указана —</option>
                  <option value="director">Директор</option>
                  <option value="safety_manager">Начальник ПБ</option>
                  <option value="engineer">Инженер</option>
                  <option value="other">Другое</option>
                </select>
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
        ) : persons.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--gray-400)' }}>Нет записей</div>
        ) : (
          <table className="data-table">
            <thead><tr><th>ФИО</th><th>Организация</th><th>Должность</th><th>Роль</th><th>Телефон</th><th></th></tr></thead>
            <tbody>
              {persons.map(p => (
                <tr key={p.id}>
                  <td><strong>{p.full_name}</strong></td>
                  <td>{orgName(p.organization_id)}</td>
                  <td>{p.position || '—'}</td>
                  <td>{roleLabel(p.role)}</td>
                  <td>{p.phone || '—'}</td>
                  <td>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button className="btn btn-ghost btn-sm" onClick={() => handleEdit(p)}><i className="fas fa-edit"></i></button>
                      <button className="btn btn-ghost btn-sm" style={{ color: 'var(--danger)' }} onClick={() => handleDelete(p.id)}><i className="fas fa-trash"></i></button>
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
