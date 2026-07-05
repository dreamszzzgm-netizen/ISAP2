import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { facilitiesApi, equipmentApi, substancesApi, facilityTypesApi, opoDetailsApi, pmlaApi } from '../api';
import { statusLabels, statusBadgeClass, hazardLabel, hazardBadge } from '../constants';
import WordImportButton from '../components/WordImportButton';

const emptyEq = { name: '', equipment_type: '', serial_number: '', manufacturer: '', manufacture_year: '' };
const emptySub = { name: '', cas_number: '', quantity_kg: '', threshold_quantity_kg: '' };

const processChecks = [
  { id: '2.1', label: '2.1 Горение' },
  { id: '2.2а', label: '2.2а Взрыв' },
  { id: '2.2б', label: '2.2б Разрушение сосудов под давлением' },
  { id: '2.2в', label: '2.2в Выброс ОВ' },
  { id: '2.3', label: '2.3 Неконтролируемый розлив' },
  { id: '2.4', label: '2.4 Обрушение' },
  { id: '2.5', label: '2.5 Падение' },
  { id: '2.6', label: '2.6 Утечка' },
];

const classificationChecks = [
  { id: '4.1', label: '4.1 Взрывоопасные' },
  { id: '4.2', label: '4.2 Пожароопасные' },
  { id: '4.3', label: '4.3 Химически опасные' },
  { id: '4.4', label: '4.4 Токсичные' },
  { id: '4.5', label: '4.5 Высокотемпературные' },
  { id: '4.6', label: '4.6 Давление' },
  { id: '4.7', label: '4.7 Энергетические' },
];

function ProgressRing({ percent, size = 60, stroke = 5 }) {
  const radius = (size - stroke) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (percent / 100) * circumference;
  return (
    <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
      <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke="var(--gray-100)" strokeWidth={stroke} />
      <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke={percent === 100 ? 'var(--success)' : 'var(--primary)'} strokeWidth={stroke}
        strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round" />
      <text x={size/2} y={size/2} textAnchor="middle" dominantBaseline="central"
        style={{ transform: 'rotate(90deg)', transformOrigin: 'center', fontSize: 13, fontWeight: 700, fill: 'var(--gray-700)' }}>
        {percent}%
      </text>
    </svg>
  );
}

function StatCard({ icon, label, value, color = 'var(--primary)' }) {
  return (
    <div className="stat-card">
      <div className="stat-icon" style={{ background: color + '15', color }}>{icon}</div>
      <div className="stat-info">
        <div className="stat-value">{value}</div>
        <div className="stat-label">{label}</div>
      </div>
    </div>
  );
}

function InlineForm({ fields, values, onChange, onSubmit, onCancel, submitLabel }) {
  return (
    <div className="form-section">
      <div className="form-grid">
        {fields.map(f => (
          <div key={f.key} className="form-group">
            <label className="form-label">{f.label}</label>
            <input className="form-input" value={values[f.key] || ''} onChange={e => onChange({ ...values, [f.key]: e.target.value })} />
          </div>
        ))}
      </div>
      <div className="form-actions">
        <button className="btn btn-primary btn-sm" onClick={onSubmit}>{submitLabel}</button>
        <button className="btn btn-secondary btn-sm" onClick={onCancel}>Отмена</button>
      </div>
    </div>
  );
}

const eqFields = [
  { key: 'name', label: 'Наименование *' },
  { key: 'equipment_type', label: 'Тип оборудования' },
  { key: 'serial_number', label: 'Зав. номер' },
  { key: 'manufacturer', label: 'Производитель' },
  { key: 'manufacture_year', label: 'Год выпуска' },
];

const subFields = [
  { key: 'name', label: 'Наименование *' },
  { key: 'cas_number', label: 'CAS номер' },
  { key: 'quantity_kg', label: 'Количество, кг' },
  { key: 'threshold_quantity_kg', label: 'Пороговое кол-во, кг' },
];

function calcOpoProgress(form) {
  let filled = 0, total = 0;
  const checks = ['f1_1', 'f1_2', 'f1_3', 'f1_4', 'danger_class', 'f8_1_1', 'f8_1_3', 'f9_5'];
  checks.forEach(k => { total++; if (form[k]?.trim()) filled++; });
  if (form.composition?.length > 0) filled++;
  total++;
  if (form.processes_text) filled++;
  total++;
  return Math.round((filled / total) * 100);
}

export default function FacilityDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [facility, setFacility] = useState(null);
  const [equipment, setEquipment] = useState([]);
  const [substances, setSubstances] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [facilityTypes, setFacilityTypes] = useState([]);
  const [opoForm, setOpoForm] = useState({});
  const [hasDetails, setHasDetails] = useState(false);
  const [tab, setTab] = useState('dashboard');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [showEqForm, setShowEqForm] = useState(false);
  const [editEqId, setEditEqId] = useState(null);
  const [eqForm, setEqForm] = useState(emptyEq);
  const [showSubForm, setShowSubForm] = useState(false);
  const [editSubId, setEditSubId] = useState(null);
  const [subForm, setSubForm] = useState(emptySub);

  const [error, setError] = useState(null);
  const [success, setSuccess] = useState('');

  const load = async () => {
    try {
      const [fullFac, types, opoDetails] = await Promise.all([
        facilitiesApi.getFull(id),
        facilityTypesApi.list(),
        opoDetailsApi.get(id),
      ]);
      setFacility(fullFac);
      setEquipment(fullFac.equipment || []);
      setSubstances(fullFac.substances || []);
      setDocuments(fullFac.documents || []);
      setFacilityTypes(types);
      if (opoDetails._has_details) {
        const { _has_details, ...formData } = opoDetails;
        setOpoForm(formData);
        setHasDetails(true);
      } else {
        setOpoForm({
          f1_1: fullFac.name || '', f1_4: fullFac.address || '',
          danger_class: fullFac.hazard_class?.toString() || '',
          f1_2: fullFac.facility_type || '', f1_3: fullFac.reg_number || '',
          composition: [], processes: {}, classification: {},
        });
      }
    } catch (e) { setError(e.message || 'Ошибка загрузки'); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [id]);

  const handleSaveOpo = async () => {
    setSaving(true); setError(null); setSuccess('');
    try {
      const data = {
        ...opoForm,
        processes_text: processChecks.filter(c => opoForm.processes?.[c.id]).map(c => c.id).join(', '),
        classification_text: classificationChecks.filter(c => opoForm.classification?.[c.id]).map(c => c.id).join(', '),
      };
      await opoDetailsApi.save(id, data);
      setHasDetails(true);
      setSuccess('Сведения ОПО сохранены');
    } catch (e) { setError(e.message); }
    finally { setSaving(false); }
  };

  const handleExport = async (format) => {
    try {
      const blob = format === 'pdf' ? await opoDetailsApi.exportPdf(id) : await opoDetailsApi.exportDocx(id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = `Сведения_об_ОПО.${format}`; a.click();
      URL.revokeObjectURL(url);
    } catch (e) { setError(`Ошибка экспорта: ${e.message}`); }
  };

  const handleWordImport = (data, warnings) => {
    setOpoForm(prev => ({ ...prev, ...data }));
    setSuccess('Данные импортированы из Word');
  };

  const handleGeneratePmla = async () => {
    try {
      const result = await pmlaApi.generate(id);
      navigate('/documents');
    } catch (e) { setError(e.message); }
  };

  const resetEqForm = () => { setEqForm(emptyEq); setEditEqId(null); setShowEqForm(false); };
  const handleEqSubmit = async () => {
    if (!eqForm.name.trim()) return;
    try {
      const data = { hazardous_facility_id: id, name: eqForm.name, equipment_type: eqForm.equipment_type || null, serial_number: eqForm.serial_number || null, manufacturer: eqForm.manufacturer || null, manufacture_year: eqForm.manufacture_year ? parseInt(eqForm.manufacture_year) : null };
      if (editEqId) await equipmentApi.update(editEqId, data); else await equipmentApi.create(data);
      resetEqForm(); await load();
    } catch (e) { setError(e.message); }
  };
  const handleEqEdit = (eq) => { setEditEqId(eq.id); setEqForm({ name: eq.name, equipment_type: eq.equipment_type || '', serial_number: eq.serial_number || '', manufacturer: eq.manufacturer || '', manufacture_year: eq.manufacture_year?.toString() || '' }); setShowEqForm(true); };
  const handleEqDelete = async (eqId) => { if (!confirm('Удалить?')) return; try { await equipmentApi.delete(eqId); await load(); } catch (e) { setError(e.message); } };

  const resetSubForm = () => { setSubForm(emptySub); setEditSubId(null); setShowSubForm(false); };
  const handleSubSubmit = async () => {
    if (!subForm.name.trim()) return;
    try {
      const data = { hazardous_facility_id: id, name: subForm.name, cas_number: subForm.cas_number || null, quantity_kg: subForm.quantity_kg ? parseFloat(subForm.quantity_kg) : null, threshold_quantity_kg: subForm.threshold_quantity_kg ? parseFloat(subForm.threshold_quantity_kg) : null };
      if (editSubId) await substancesApi.update(editSubId, data); else await substancesApi.create(data);
      resetSubForm(); await load();
    } catch (e) { setError(e.message); }
  };
  const handleSubEdit = (sub) => { setEditSubId(sub.id); setSubForm({ name: sub.name, cas_number: sub.cas_number || '', quantity_kg: sub.quantity_kg?.toString() || '', threshold_quantity_kg: sub.threshold_quantity_kg?.toString() || '' }); setShowSubForm(true); };
  const handleSubDelete = async (subId) => { if (!confirm('Удалить?')) return; try { await substancesApi.delete(subId); await load(); } catch (e) { setError(e.message); } };

  if (loading) return <div className="loading-center"><div className="spinner"></div></div>;
  if (!facility) return null;

  const typeName = facilityTypes.find(t => t.code === facility.facility_type)?.name || facility.facility_type || '—';
  const opoProgress = calcOpoProgress(opoForm);
  const lastDoc = documents[0];

  return (
    <div>
      <button className="btn btn-ghost mb-16" style={{ padding: 0 }} onClick={() => navigate('/facilities')}>
        <i className="fas fa-arrow-left"></i> К списку объектов
      </button>

      {/* Header карточки */}
      <div className="facility-header">
        <div className="facility-header-main">
          <div>
            <div className="facility-header-title">
              {facility.name}
              {facility.hazard_class && <span className={`badge ${hazardBadge(facility.hazard_class)}`}>{hazardLabel(facility.hazard_class)}</span>}
            </div>
            <div className="facility-header-sub">{typeName} | {facility.reg_number || 'Рег. № не указан'}</div>
          </div>
        </div>
        <div className="facility-header-actions">
          <button className="btn btn-primary" onClick={handleGeneratePmla}>
            <i className="fas fa-file-shield"></i> Сгенерировать ПМЛА
          </button>
          <button className="btn btn-secondary" onClick={() => handleExport('docx')}>
            <i className="fas fa-file-export"></i> Экспорт ОПО
          </button>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      {/* Табы */}
      <div className="tabs">
        <button className={`tab ${tab === 'dashboard' ? 'active' : ''}`} onClick={() => setTab('dashboard')}>
          <i className="fas fa-chart-line"></i> Обзор
        </button>
        <button className={`tab ${tab === 'opo' ? 'active' : ''}`} onClick={() => setTab('opo')}>
          <i className="fas fa-file-alt"></i> Сведения ОПО {hasDetails && <span className="tab-badge">{opoProgress}%</span>}
        </button>
        <button className={`tab ${tab === 'equipment' ? 'active' : ''}`} onClick={() => setTab('equipment')}>
          <i className="fas fa-cogs"></i> Оборудование ({equipment.length})
        </button>
        <button className={`tab ${tab === 'substances' ? 'active' : ''}`} onClick={() => setTab('substances')}>
          <i className="fas fa-flask"></i> Вещества ({substances.length})
        </button>
        <button className={`tab ${tab === 'documents' ? 'active' : ''}`} onClick={() => setTab('documents')}>
          <i className="fas fa-file-shield"></i> ПМЛА ({documents.length})
        </button>
      </div>

      {/* === Вкладка: Дашборд === */}
      {tab === 'dashboard' && (
        <div>
          <div className="stats-grid">
            <StatCard icon={<i className="fas fa-cogs"></i>} label="Оборудование" value={equipment.length} />
            <StatCard icon={<i className="fas fa-flask"></i>} label="Вещества" value={substances.length} color="var(--warning)" />
            <StatCard icon={<i className="fas fa-file-shield"></i>} label="Документов" value={documents.length} color="var(--success)" />
            <div className="stat-card" style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <ProgressRing percent={opoProgress} />
              <div>
                <div className="stat-label">Готовность ОПО</div>
                <div style={{ fontSize: 12, color: 'var(--gray-500)', marginTop: 4 }}>
                  {hasDetails ? 'Заполнено' : 'Не заполнено'}
                </div>
              </div>
            </div>
          </div>

          <div className="section">
            <div className="section-header">
              <div className="section-title">Основные сведения</div>
            </div>
            <div className="detail-grid">
              <div className="detail-item">
                <div className="detail-label">Наименование</div>
                <div className="detail-value">{facility.name}</div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Тип объекта</div>
                <div className="detail-value">{typeName}</div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Класс опасности</div>
                <div className="detail-value">{facility.hazard_class ? hazardLabel(facility.hazard_class) : '—'}</div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Рег. номер</div>
                <div className="detail-value">{facility.reg_number || '—'}</div>
              </div>
              <div className="detail-item" style={{ gridColumn: '1 / -1' }}>
                <div className="detail-label">Адрес</div>
                <div className="detail-value">{facility.address || '—'}</div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Инв. номер</div>
                <div className="detail-value">{facility.inventory_number || '—'}</div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Дата ввода</div>
                <div className="detail-value">{facility.commissioning_date || '—'}</div>
              </div>
            </div>
          </div>

          {lastDoc && (
            <div className="section">
              <div className="section-header">
                <div className="section-title">Последний документ</div>
                <Link to="/documents" className="btn btn-ghost btn-sm">Все документы <i className="fas fa-arrow-right"></i></Link>
              </div>
              <div style={{ padding: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <strong>{lastDoc.title || 'ПМЛА'}</strong>
                  <span className={`badge ${statusBadgeClass[lastDoc.status] || 'badge-draft'}`}>{statusLabels[lastDoc.status] || lastDoc.status}</span>
                  <span style={{ color: 'var(--gray-400)', fontSize: 13 }}>{lastDoc.created_at ? new Date(lastDoc.created_at).toLocaleDateString('ru-RU') : ''}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* === Вкладка: Сведения ОПО (встроенная форма) === */}
      {tab === 'opo' && (
        <div className="section">
          <div className="section-header">
            <div>
              <div className="section-title">Сведения, характеризующие ОПО</div>
              <div style={{ fontSize: 13, color: 'var(--gray-500)', marginTop: 4 }}>Заполните форму для генерации ПМЛА</div>
            </div>
            <div className="section-actions" style={{ display: 'flex', gap: 8 }}>
              <WordImportButton onImport={handleWordImport} />
              <button className="btn btn-secondary btn-sm" onClick={() => handleExport('docx')}><i className="fas fa-download"></i> DOCX</button>
              <button className="btn btn-secondary btn-sm" onClick={() => handleExport('pdf')}><i className="fas fa-download"></i> PDF</button>
            </div>
          </div>

          <div style={{ padding: 24 }}>
            {/* Прогресс */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24, padding: 16, background: 'var(--gray-50)', borderRadius: 'var(--radius)' }}>
              <ProgressRing percent={opoProgress} size={50} stroke={4} />
              <div>
                <div style={{ fontWeight: 600 }}>Прогресс заполнения: {opoProgress}%</div>
                <div style={{ fontSize: 13, color: 'var(--gray-500)' }}>{opoProgress === 100 ? 'Форма заполнена полностью' : 'Заполните обязательные поля для генерации ПМЛА'}</div>
              </div>
            </div>

            {/* Раздел 1: ОПО */}
            <div className="form-section mb-16">
              <div className="form-section-title">1. ОПО</div>
              <div className="form-grid">
                <div className="form-group"><label className="form-label">Полное наименование ОПО *</label><input className="form-input" value={opoForm.f1_1 || ''} onChange={e => setOpoForm({ ...opoForm, f1_1: e.target.value })} /></div>
                <div className="form-group"><label className="form-label">Тип объекта</label><input className="form-input" value={opoForm.f1_2 || ''} onChange={e => setOpoForm({ ...opoForm, f1_2: e.target.value })} /></div>
                <div className="form-group"><label className="form-label">Регистрационный номер</label><input className="form-input" value={opoForm.f1_3 || ''} onChange={e => setOpoForm({ ...opoForm, f1_3: e.target.value })} /></div>
                <div className="form-group"><label className="form-label">Адрес *</label><input className="form-input" value={opoForm.f1_4 || ''} onChange={e => setOpoForm({ ...opoForm, f1_4: e.target.value })} /></div>
                <div className="form-group"><label className="form-label">Класс опасности *</label><input className="form-input" value={opoForm.danger_class || ''} onChange={e => setOpoForm({ ...opoForm, danger_class: e.target.value })} /></div>
                <div className="form-group"><label className="form-label">Инвентарный номер</label><input className="form-input" value={opoForm.f1_7_1 || ''} onChange={e => setOpoForm({ ...opoForm, f1_7_1: e.target.value })} /></div>
              </div>
            </div>

            {/* Процессы */}
            <div className="form-section mb-16">
              <div className="form-section-title">2. Характерные процессы</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {processChecks.map(c => (
                  <label key={c.id} className={`check-chip ${opoForm.processes?.[c.id] ? 'active' : ''}`}>
                    <input type="checkbox" checked={!!opoForm.processes?.[c.id]} onChange={e => setOpoForm({ ...opoForm, processes: { ...opoForm.processes, [c.id]: e.target.checked } })} style={{ display: 'none' }} />
                    {c.label}
                  </label>
                ))}
              </div>
            </div>

            {/* Классификация */}
            <div className="form-section mb-16">
              <div className="form-section-title">3. Классификация ОПО</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {classificationChecks.map(c => (
                  <label key={c.id} className={`check-chip ${opoForm.classification?.[c.id] ? 'active' : ''}`}>
                    <input type="checkbox" checked={!!opoForm.classification?.[c.id]} onChange={e => setOpoForm({ ...opoForm, classification: { ...opoForm.classification, [c.id]: e.target.checked } })} style={{ display: 'none' }} />
                    {c.label}
                  </label>
                ))}
              </div>
            </div>

            {/* Состав */}
            <div className="form-section mb-16">
              <div className="form-section-title">4. Состав ОПО (оборудование / вещества)</div>
              {(opoForm.composition || []).map((row, i) => (
                <div key={i} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr auto', gap: 8, marginBottom: 8, alignItems: 'center' }}>
                  <input className="form-input" placeholder="Наименование" value={row.name} onChange={e => { const c = [...opoForm.composition]; c[i] = { ...c[i], name: e.target.value }; setOpoForm({ ...opoForm, composition: c }); }} />
                  <input className="form-input" placeholder="Опасность" value={row.danger} onChange={e => { const c = [...opoForm.composition]; c[i] = { ...c[i], danger: e.target.value }; setOpoForm({ ...opoForm, composition: c }); }} />
                  <input className="form-input" placeholder="Вещество" value={row.substance} onChange={e => { const c = [...opoForm.composition]; c[i] = { ...c[i], substance: e.target.value }; setOpoForm({ ...opoForm, composition: c }); }} />
                  <input className="form-input" placeholder="Характеристики" value={row.characteristics} onChange={e => { const c = [...opoForm.composition]; c[i] = { ...c[i], characteristics: e.target.value }; setOpoForm({ ...opoForm, composition: c }); }} />
                  <button className="btn btn-ghost btn-sm" style={{ color: 'var(--danger)' }} onClick={() => setOpoForm({ ...opoForm, composition: opoForm.composition.filter((_, idx) => idx !== i) })}><i className="fas fa-trash"></i></button>
                </div>
              ))}
              <button className="btn btn-ghost btn-sm" onClick={() => setOpoForm({ ...opoForm, composition: [...(opoForm.composition || []), { name: '', danger: '', substance: '', characteristics: '', processes: '' }] })}>
                <i className="fas fa-plus"></i> Добавить строку
              </button>
            </div>

            {/* Организация */}
            <div className="form-section mb-16">
              <div className="form-section-title">5. Сведения о заявителе</div>
              <div className="form-grid">
                <div className="form-group"><label className="form-label">Наименование организации *</label><input className="form-input" value={opoForm.f8_1_1 || ''} onChange={e => setOpoForm({ ...opoForm, f8_1_1: e.target.value })} /></div>
                <div className="form-group"><label className="form-label">ИНН *</label><input className="form-input" value={opoForm.f8_1_3 || ''} onChange={e => setOpoForm({ ...opoForm, f8_1_3: e.target.value })} /></div>
                <div className="form-group"><label className="form-label">ОГРН</label><input className="form-input" value={opoForm.f8_1_5 || ''} onChange={e => setOpoForm({ ...opoForm, f8_1_5: e.target.value })} /></div>
                <div className="form-group"><label className="form-label">Адрес организации</label><input className="form-input" value={opoForm.f8_1_6 || ''} onChange={e => setOpoForm({ ...opoForm, f8_1_6: e.target.value })} /></div>
                <div className="form-group"><label className="form-label">Телефон</label><input className="form-input" value={opoForm.f9_5 || ''} onChange={e => setOpoForm({ ...opoForm, f9_5: e.target.value })} /></div>
                <div className="form-group"><label className="form-label">Email</label><input className="form-input" value={opoForm.f9_6 || ''} onChange={e => setOpoForm({ ...opoForm, f9_6: e.target.value })} /></div>
              </div>
            </div>

            <div className="form-actions">
              <button className="btn btn-primary" onClick={handleSaveOpo} disabled={saving}>
                {saving ? <><i className="fas fa-spinner fa-spin"></i> Сохранение...</> : <><i className="fas fa-save"></i> Сохранить сведения ОПО</>}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* === Вкладка: Оборудование === */}
      {tab === 'equipment' && (
        <div className="section">
          <div className="section-header">
            <div className="section-title">Оборудование</div>
            <button className="btn btn-primary btn-sm" onClick={() => { resetEqForm(); setShowEqForm(true); }}><i className="fas fa-plus"></i> Добавить</button>
          </div>
          {showEqForm && <div style={{ padding: 24, borderBottom: '1px solid var(--gray-100)' }}><InlineForm fields={eqFields} values={eqForm} onChange={setEqForm} onSubmit={handleEqSubmit} onCancel={resetEqForm} submitLabel={editEqId ? 'Сохранить' : 'Добавить'} /></div>}
          {equipment.length === 0 && !showEqForm ? (
            <div className="empty-state"><i className="fas fa-cogs"></i><div>Нет оборудования</div></div>
          ) : (
            <table className="data-table">
              <thead><tr><th>Наименование</th><th>Тип</th><th>Зав. номер</th><th>Производитель</th><th>Год</th><th></th></tr></thead>
              <tbody>
                {equipment.map(eq => (
                  <tr key={eq.id}>
                    <td><strong>{eq.name}</strong></td>
                    <td>{eq.equipment_type || '—'}</td>
                    <td>{eq.serial_number || '—'}</td>
                    <td>{eq.manufacturer || '—'}</td>
                    <td>{eq.manufacture_year || '—'}</td>
                    <td><div style={{ display: 'flex', gap: 4 }}><button className="btn btn-ghost btn-sm" onClick={() => handleEqEdit(eq)}><i className="fas fa-edit"></i></button><button className="btn btn-ghost btn-sm" style={{ color: 'var(--danger)' }} onClick={() => handleEqDelete(eq.id)}><i className="fas fa-trash"></i></button></div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* === Вкладка: Вещества === */}
      {tab === 'substances' && (
        <div className="section">
          <div className="section-header">
            <div className="section-title">Опасные вещества</div>
            <button className="btn btn-primary btn-sm" onClick={() => { resetSubForm(); setShowSubForm(true); }}><i className="fas fa-plus"></i> Добавить</button>
          </div>
          {showSubForm && <div style={{ padding: 24, borderBottom: '1px solid var(--gray-100)' }}><InlineForm fields={subFields} values={subForm} onChange={setSubForm} onSubmit={handleSubSubmit} onCancel={resetSubForm} submitLabel={editSubId ? 'Сохранить' : 'Добавить'} /></div>}
          {substances.length === 0 && !showSubForm ? (
            <div className="empty-state"><i className="fas fa-flask"></i><div>Нет веществ</div></div>
          ) : (
            <table className="data-table">
              <thead><tr><th>Наименование</th><th>CAS</th><th>Кол-во, кг</th><th>Порог, кг</th><th></th></tr></thead>
              <tbody>
                {substances.map(sub => (
                  <tr key={sub.id}>
                    <td><strong>{sub.name}</strong></td>
                    <td>{sub.cas_number || '—'}</td>
                    <td>{sub.quantity_kg ?? '—'}</td>
                    <td>{sub.threshold_quantity_kg ?? '—'}</td>
                    <td><div style={{ display: 'flex', gap: 4 }}><button className="btn btn-ghost btn-sm" onClick={() => handleSubEdit(sub)}><i className="fas fa-edit"></i></button><button className="btn btn-ghost btn-sm" style={{ color: 'var(--danger)' }} onClick={() => handleSubDelete(sub.id)}><i className="fas fa-trash"></i></button></div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* === Вкладка: Документы === */}
      {tab === 'documents' && (
        <div className="section">
          <div className="section-header">
            <div className="section-title">Документы ПМЛА</div>
            <button className="btn btn-primary btn-sm" onClick={handleGeneratePmla}><i className="fas fa-plus"></i> Создать ПМЛА</button>
          </div>
          {documents.length === 0 ? (
            <div className="empty-state"><i className="fas fa-file-shield"></i><div>Нет документов</div></div>
          ) : (
            <table className="data-table">
              <thead><tr><th>ID</th><th>Название</th><th>Статус</th><th>Дата</th><th></th></tr></thead>
              <tbody>
                {documents.map(doc => (
                  <tr key={doc.id}>
                    <td><span className="tag tag-blue">{doc.id?.slice(0, 8)}</span></td>
                    <td><strong>{doc.title || 'ПМЛА'}</strong></td>
                    <td><span className={`badge ${statusBadgeClass[doc.status] || 'badge-draft'}`}>{statusLabels[doc.status] || doc.status}</span></td>
                    <td>{doc.created_at ? new Date(doc.created_at).toLocaleDateString('ru-RU') : '—'}</td>
                    <td><Link to="/documents" className="btn btn-ghost btn-sm"><i className="fas fa-external-link-alt"></i></Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
