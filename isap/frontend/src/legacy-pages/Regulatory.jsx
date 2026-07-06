import React, { useState, useEffect } from 'react';
import { regulatoryApi } from '../api';
import { regulatoryStatusBadge } from '../constants';

const emptyForm = { title: '', category: 'НПА', status: 'действует', notes: '' };

export default function Regulatory() {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterCategory, setFilterCategory] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const loadDocs = () => {
    regulatoryApi.list()
      .then(setDocs)
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadDocs(); }, []);

  const categoryLabel = (cat) => {
    const labels = { 'НПА': 'НПА', 'рекомендация': 'Рекомендация', 'методика расчёта': 'Методика' };
    return labels[cat] || cat;
  };

  const filtered = docs.filter(d => {
    if (filterCategory && d.category !== filterCategory) return false;
    if (filterStatus && d.status !== filterStatus) return false;
    return true;
  });

  const resetForm = () => { setForm(emptyForm); setEditId(null); setShowForm(false); setError(''); };

  const handleEdit = (doc) => {
    setEditId(doc.id);
    setForm({ title: doc.title, category: doc.category, status: doc.status, notes: doc.notes || '' });
    setShowForm(true);
  };

  const handleSubmit = async () => {
    if (!form.title.trim()) { setError('Введите наименование'); return; }
    setSaving(true);
    setError('');
    try {
      if (editId) {
        await regulatoryApi.update(editId, form);
      } else {
        await regulatoryApi.create(form);
      }
      resetForm();
      loadDocs();
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Удалить нормативный документ?')) return;
    try {
      await regulatoryApi.delete(id);
      loadDocs();
    } catch (e) {
      alert(e.message);
    }
  };

  return (
    <div>
      <div className="section">
        <div className="section-header">
          <div className="section-title">Нормативные документы</div>
          <div className="section-actions">
            <span style={{ fontSize: 13, color: 'var(--gray-500)', marginRight: 12 }}>Всего: {docs.length}</span>
            <button className="btn btn-primary btn-sm" onClick={() => { resetForm(); setShowForm(true); }}>
              <i className="fas fa-plus"></i> Добавить
            </button>
          </div>
        </div>

        <div style={{ padding: '16px 24px', display: 'flex', gap: 16, borderBottom: '1px solid var(--gray-100)' }}>
          <div className="form-group" style={{ maxWidth: 250 }}>
            <select className="form-select" value={filterCategory} onChange={e => setFilterCategory(e.target.value)}>
              <option value="">Все категории</option>
              <option value="НПА">НПА</option>
              <option value="рекомендация">Рекомендации</option>
              <option value="методика расчёта">Методики</option>
            </select>
          </div>
          <div className="form-group" style={{ maxWidth: 250 }}>
            <select className="form-select" value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
              <option value="">Все статусы</option>
              <option value="действует">Действует</option>
              <option value="спорный">Спорный</option>
              <option value="заменён">Заменён</option>
              <option value="отменён">Отменён</option>
            </select>
          </div>
        </div>

        {showForm && (
          <div style={{ padding: 24, borderBottom: '1px solid var(--gray-100)', background: 'var(--gray-50)' }}>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: 'var(--gray-700)' }}>
              {editId ? 'Редактирование документа' : 'Новый нормативный документ'}
            </div>
            {error && <div style={{ padding: '8px 12px', background: 'var(--danger-light)', color: 'var(--danger)', borderRadius: 6, marginBottom: 12, fontSize: 13 }}>{error}</div>}
            <div className="form-grid" style={{ marginBottom: 16 }}>
              <div className="form-group full">
                <label className="form-label">Наименование <span className="required">*</span></label>
                <input className="form-input" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} placeholder="Федеральный закон от 21.07.1997 №116-ФЗ..." />
              </div>
              <div className="form-group">
                <label className="form-label">Категория</label>
                <select className="form-select" value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}>
                  <option value="НПА">НПА</option>
                  <option value="рекомендация">Рекомендация</option>
                  <option value="методика расчёта">Методика расчёта</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Статус</label>
                <select className="form-select" value={form.status} onChange={e => setForm({ ...form, status: e.target.value })}>
                  <option value="действует">Действует</option>
                  <option value="спорный">Спорный</option>
                  <option value="заменён">Заменён</option>
                  <option value="отменён">Отменён</option>
                </select>
              </div>
              <div className="form-group full">
                <label className="form-label">Примечания</label>
                <textarea className="form-input" rows={3} value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} placeholder="Дополнительная информация о документе..." style={{ resize: 'vertical' }} />
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-primary btn-sm" onClick={handleSubmit} disabled={saving}>
                {saving ? 'Сохранение...' : editId ? 'Сохранить' : 'Создать'}
              </button>
              <button className="btn btn-secondary btn-sm" onClick={resetForm}>Отмена</button>
            </div>
          </div>
        )}

        {loading ? (
          <div className="loading-center"><div className="spinner"></div></div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--gray-400)' }}>
            <i className="fas fa-book" style={{ fontSize: 40, marginBottom: 12, display: 'block' }}></i>
            <div>Нет документов</div>
            <button className="btn btn-primary btn-sm" style={{ marginTop: 16 }} onClick={() => { resetForm(); setShowForm(true); }}>
              <i className="fas fa-plus"></i> Добавить первый документ
            </button>
          </div>
        ) : (
          <table className="data-table">
            <thead><tr><th>Наименование</th><th>Категория</th><th>Статус</th><th>Примечания</th><th></th></tr></thead>
            <tbody>
              {filtered.map(doc => (
                <tr key={doc.id}>
                  <td><strong>{doc.title}</strong></td>
                  <td><span className="tag tag-blue">{categoryLabel(doc.category)}</span></td>
                  <td>
                    <span className={`badge ${regulatoryStatusBadge[doc.status] || 'badge-draft'}`}>
                      {doc.status}
                    </span>
                  </td>
                  <td style={{ fontSize: 12, color: 'var(--gray-500)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {doc.notes || '—'}
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button className="btn btn-ghost btn-sm" onClick={() => handleEdit(doc)} title="Редактировать"><i className="fas fa-edit"></i></button>
                      <button className="btn btn-ghost btn-sm" style={{ color: 'var(--danger)' }} onClick={() => handleDelete(doc.id)} title="Удалить"><i className="fas fa-trash"></i></button>
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
