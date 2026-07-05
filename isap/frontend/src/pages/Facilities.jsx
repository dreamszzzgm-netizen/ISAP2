import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { facilitiesApi, organizationsApi, facilityTypesApi } from '../api';
import { hazardLabel, hazardBadge, orgName as orgNameUtil } from '../constants';

const emptyForm = {
  name: '', organization_id: '', facility_type: '', reg_number: '',
  hazard_class: '', address: '', latitude: '', longitude: '',
  commissioning_date: '', inventory_number: '',
};

export default function Facilities() {
  const [facilities, setFacilities] = useState([]);
  const [organizations, setOrganizations] = useState([]);
  const [facilityTypes, setFacilityTypes] = useState([]);
  const [selectedOrg, setSelectedOrg] = useState('');
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const [facs, orgs, types] = await Promise.all([
        facilitiesApi.list(selectedOrg || null),
        organizationsApi.list(),
        facilityTypesApi.list(),
      ]);
      setFacilities(facs);
      setOrganizations(orgs);
      setFacilityTypes(types);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [selectedOrg]);

  const orgName = (id) => orgNameUtil(organizations, id);

  const typeName = (code) => facilityTypes.find(t => t.code === code)?.name || code || '—';

  const resetForm = () => { setForm(emptyForm); setEditingId(null); setShowForm(false); };

  const handleSubmit = async () => {
    if (!form.name.trim() || !form.organization_id) return;
    setError(null);
    try {
      const data = {
        name: form.name,
        organization_id: form.organization_id,
        facility_type: form.facility_type || null,
        reg_number: form.reg_number || null,
        hazard_class: form.hazard_class ? parseInt(form.hazard_class) : null,
        address: form.address || null,
        latitude: form.latitude ? parseFloat(form.latitude) : null,
        longitude: form.longitude ? parseFloat(form.longitude) : null,
        commissioning_date: form.commissioning_date || null,
        inventory_number: form.inventory_number || null,
      };
      if (editingId) {
        await facilitiesApi.update(editingId, data);
      } else {
        await facilitiesApi.create(data);
      }
      resetForm();
      await load();
    } catch (e) { setError(e.message); }
  };

  const handleEdit = (fac) => {
    setEditingId(fac.id);
    setForm({
      name: fac.name,
      organization_id: fac.organization_id || '',
      facility_type: fac.facility_type || '',
      reg_number: fac.reg_number || '',
      hazard_class: fac.hazard_class?.toString() || '',
      address: fac.address || '',
      latitude: fac.latitude?.toString() || '',
      longitude: fac.longitude?.toString() || '',
      commissioning_date: fac.commissioning_date || '',
      inventory_number: fac.inventory_number || '',
    });
    setShowForm(true);
  };

  const handleDelete = async (id) => {
    if (!confirm('Удалить объект?')) return;
    try { await facilitiesApi.delete(id); await load(); } catch (e) { setError(e.message); }
  };

  const handleChange = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  // Автоподстановка класса опасности при выборе типа
  const handleTypeChange = (e) => {
    const code = e.target.value;
    const type = facilityTypes.find(t => t.code === code);
    setForm({
      ...form,
      facility_type: code,
      hazard_class: (type?.hazard_class_default?.toString()) || form.hazard_class,
    });
  };

  return (
    <div>
      <div className="section">
        <div className="section-header">
          <div className="section-title">Объекты ОПО</div>
          <div className="section-actions">
            {!showForm && (
              <button className="btn btn-primary btn-sm" onClick={() => { resetForm(); setShowForm(true); }}>
                <i className="fas fa-plus"></i> Добавить объект
              </button>
            )}
          </div>
        </div>

        <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--gray-100)' }}>
          <div className="form-group" style={{ maxWidth: 300 }}>
            <select className="form-select" value={selectedOrg} onChange={e => setSelectedOrg(e.target.value)}>
              <option value="">Все организации</option>
              {organizations.map(org => <option key={org.id} value={org.id}>{org.name}</option>)}
            </select>
          </div>
        </div>

        {showForm && (
          <div style={{ padding: 24, borderBottom: '1px solid var(--gray-100)', background: 'var(--gray-50)' }}>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: 'var(--gray-700)' }}>
              {editingId ? 'Редактирование объекта' : 'Новый объект'}
            </div>
            <div className="form-grid">
              <div className="form-group">
                <label className="form-label">Наименование <span className="required">*</span></label>
                <input className="form-input" value={form.name} onChange={handleChange('name')} placeholder="Компрессорная станция №1" />
              </div>
              <div className="form-group">
                <label className="form-label">Организация <span className="required">*</span></label>
                <select className="form-select" value={form.organization_id} onChange={handleChange('organization_id')}>
                  <option value="">— Выберите —</option>
                  {organizations.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Тип объекта ОПО</label>
                <select className="form-select" value={form.facility_type} onChange={handleTypeChange}>
                  <option value="">— Выберите тип —</option>
                  {facilityTypes.map(t => (
                    <option key={t.code} value={t.code}>{t.name}</option>
                  ))}
                </select>
                {form.facility_type && (
                  <div style={{ fontSize: 12, color: 'var(--gray-500)', marginTop: 4 }}>
                    {facilityTypes.find(t => t.code === form.facility_type)?.description}
                  </div>
                )}
              </div>
              <div className="form-group">
                <label className="form-label">Класс опасности</label>
                <select className="form-select" value={form.hazard_class} onChange={handleChange('hazard_class')}>
                  <option value="">— Не указан —</option>
                  <option value="1">I — Чрезвычайно высокая</option>
                  <option value="2">II — Высокая</option>
                  <option value="3">III — Умеренная</option>
                  <option value="4">IV — Низкая</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Рег. номер</label>
                <input className="form-input" value={form.reg_number} onChange={handleChange('reg_number')} placeholder="77-1-XX-XXXX" />
              </div>
              <div className="form-group">
                <label className="form-label">Инвентарный номер</label>
                <input className="form-input" value={form.inventory_number} onChange={handleChange('inventory_number')} placeholder="ИНВ-001" />
              </div>
              <div className="form-group full">
                <label className="form-label">Адрес</label>
                <input className="form-input" value={form.address} onChange={handleChange('address')} placeholder="г. Тюмень, ул. Промышленная, д. 10" />
              </div>
              <div className="form-group">
                <label className="form-label">Широта (lat)</label>
                <input className="form-input" type="number" step="0.0000001" value={form.latitude} onChange={handleChange('latitude')} placeholder="57.1522" />
              </div>
              <div className="form-group">
                <label className="form-label">Долгота (lng)</label>
                <input className="form-input" type="number" step="0.0000001" value={form.longitude} onChange={handleChange('longitude')} placeholder="65.5272" />
              </div>
              <div className="form-group">
                <label className="form-label">Дата ввода в эксплуатацию</label>
                <input className="form-input" type="date" value={form.commissioning_date} onChange={handleChange('commissioning_date')} />
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
        ) : facilities.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--gray-400)' }}>
            <i className="fas fa-industry" style={{ fontSize: 40, marginBottom: 12, display: 'block' }}></i>
            <div>Нет объектов</div>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Наименование</th>
                <th>Организация</th>
                <th>Тип</th>
                <th>Рег. номер</th>
                <th>Класс опасности</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {facilities.map(fac => (
                <tr key={fac.id}>
                  <td><Link to={`/facilities/${fac.id}`} style={{ color: 'var(--primary)', textDecoration: 'none', fontWeight: 600 }}>{fac.name}</Link></td>
                  <td>{orgName(fac.organization_id)}</td>
                  <td>{typeName(fac.facility_type)}</td>
                  <td>{fac.reg_number || '—'}</td>
                  <td>
                    {fac.hazard_class ? (
                      <span className={`badge ${hazardBadge(fac.hazard_class)}`}>{hazardLabel(fac.hazard_class)}</span>
                    ) : '—'}
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button className="btn btn-ghost btn-sm" onClick={() => handleEdit(fac)}><i className="fas fa-edit"></i></button>
                      <button className="btn btn-ghost btn-sm" style={{ color: 'var(--danger)' }} onClick={() => handleDelete(fac.id)}><i className="fas fa-trash"></i></button>
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
