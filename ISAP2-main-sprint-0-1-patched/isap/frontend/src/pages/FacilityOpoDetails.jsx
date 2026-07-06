import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { facilitiesApi, opoDetailsApi } from '../api';
import WordImportButton from '../components/WordImportButton';

const emptyForm = {
  f1_1: '', f1_2: '', f1_3: '', f1_4: '', f1_5: '', f1_6: '', f1_7_1: '', f1_7_2: '',
  processes: {}, processes_text: '',
  danger_class: '',
  classification: {}, classification_text: '',
  licenses: {}, licenses_text: '',
  composition: [],
  f7: '',
  applicant_type: 'legal',
  f8_1_1: '', f8_1_2: '', f8_1_3: '', f8_1_4: '', f8_1_5: '', f8_1_6: '', f8_1_7: '', f8_1_8: '', f8_1_9: '', f8_1_10: '',
  f8_2_1: '', f8_2_2: '', f8_2_3: '', f8_2_4: '', f8_2_5: '', f8_2_6: '',
  f9_1: '', f9_2: '', f9_3: '', f9_4: '', f9_5: '', f9_6: '', f9_7: '', f9_8: '', f9_10: '', f9_11: '',
  signDolj: '', signPodp: '', signDate: '', signMp: '',
};

const emptyRow = { name: '', danger: '', substance: '', characteristics: '', processes: '' };

const processChecks = [
  { id: '2.1', label: '2.1 Горение (горючих веществ)' },
  { id: '2.2а', label: '2.2а Взрыв' },
  { id: '2.2б', label: '2.2б Разрушение сосудов под давлением' },
  { id: '2.2в', label: '2.2в Выброс опасных веществ' },
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
  { id: '4.8', label: '4.8 Биологические' },
  { id: '4.9', label: '4.9 Радиационные' },
  { id: '4.10', label: '4.10 Комбинированные' },
  { id: '4.11', label: '4.11 Прочие' },
];

const licenseChecks = [
  { id: '5.1', label: '5.1 Подземное хранение' },
  { id: '5.2', label: '5.2 Хранение и транспортирование' },
  { id: '5.3', label: '5.3 Перевозка' },
  { id: '5.4', label: '5.4 Использование' },
  { id: '5.5', label: '5.5 Утилизация' },
  { id: '5.6', label: '5.6 Захоронение' },
  { id: '5.7', label: '5.7 Ликвидация' },
];

export default function FacilityOpoDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [facility, setFacility] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState('');

  useEffect(() => {
    const load = async () => {
      try {
        const [fac, details] = await Promise.all([
          facilitiesApi.get(id),
          opoDetailsApi.get(id),
        ]);
        setFacility(fac);
        if (details._has_details) {
          const { _has_details, ...formData } = details;
          setForm({ ...emptyForm, ...formData });
        } else {
          setForm({ ...emptyForm, f1_1: fac.name || '', f1_4: fac.address || '', danger_class: fac.hazard_class?.toString() || '' });
        }
      } catch (e) { setError(e.message); }
      finally { setLoading(false); }
    };
    load();
  }, [id]);

  const handleChange = (field) => (e) => {
    const val = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
    setForm({ ...form, [field]: val });
  };

  const handleCompositionChange = (index, field, value) => {
    const comp = [...form.composition];
    comp[index] = { ...comp[index], [field]: value };
    setForm({ ...form, composition: comp });
  };

  const addCompositionRow = () => setForm({ ...form, composition: [...form.composition, { ...emptyRow }] });
  const removeCompositionRow = (i) => setForm({ ...form, composition: form.composition.filter((_, idx) => idx !== i) });

  const buildCheckedText = (checks, state) => {
    return checks.filter(c => state[c.id]).map(c => c.id).join(', ');
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess('');
    try {
      const data = {
        ...form,
        processes_text: buildCheckedText(processChecks, form.processes),
        classification_text: buildCheckedText(classificationChecks, form.classification),
        licenses_text: buildCheckedText(licenseChecks, form.licenses),
      };
      await opoDetailsApi.save(id, data);
      setSuccess('Данные сохранены');
    } catch (e) { setError(e.message); }
    finally { setSaving(false); }
  };

  const handleExport = async (format) => {
    try {
      const blob = format === 'pdf'
        ? await opoDetailsApi.exportPdf(id)
        : await opoDetailsApi.exportDocx(id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Сведения_об_ОПО.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) { setError(`Ошибка экспорта: ${e.message}`); }
  };

  const handleWordImport = (data, warnings) => {
    setForm(prev => ({ ...prev, ...data }));
    if (warnings.length > 0) setSuccess('Импорт завершён. Предупреждения: ' + warnings.join('; '));
    else setSuccess('Данные импортированы из Word');
  };

  if (loading) return <div className="loading-center"><div className="spinner"></div></div>;
  if (!facility) return null;

  return (
    <div>
      <button className="btn btn-ghost" style={{ marginBottom: 16, padding: 0 }} onClick={() => navigate(`/facilities/${id}`)}>
        <i className="fas fa-arrow-left"></i> К объекту
      </button>

      <div className="section">
        <div className="section-header">
          <div>
            <div className="section-title">Сведения, характеризующие ОПО</div>
            <div style={{ fontSize: 13, color: 'var(--gray-500)' }}>{facility.name}</div>
          </div>
          <div className="section-actions">
            <WordImportButton onImport={handleWordImport} />
          </div>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      {/* Раздел 1 */}
      <div className="section mb-16">
        <div className="section-subtitle">1. ОПО</div>
        <div className="form-grid">
          <div className="form-group full">
            <label className="form-label">1.1. Полное наименование ОПО <span className="required">*</span></label>
            <input className="form-input" value={form.f1_1} onChange={handleChange('f1_1')} />
          </div>
          <div className="form-group full">
            <label className="form-label">1.2. Типовое наименование</label>
            <input className="form-input" value={form.f1_2} onChange={handleChange('f1_2')} />
          </div>
          <div className="form-group full">
            <label className="form-label">1.3. Цифровое обозначение раздела отраслевой принадлежности</label>
            <input className="form-input" value={form.f1_3} onChange={handleChange('f1_3')} />
          </div>
          <div className="form-group full">
            <label className="form-label">1.4. Место нахождения ОПО <span className="required">*</span></label>
            <input className="form-input" value={form.f1_4} onChange={handleChange('f1_4')} />
          </div>
          <div className="form-group">
            <label className="form-label">1.5. ОКТМО</label>
            <input className="form-input" value={form.f1_5} onChange={handleChange('f1_5')} />
          </div>
          <div className="form-group">
            <label className="form-label">1.6. Дата ввода в эксплуатацию</label>
            <input className="form-input" type="date" value={form.f1_6} onChange={handleChange('f1_6')} />
          </div>
          <div className="form-group full">
            <label className="form-label">1.7. Наименование и ИНН собственника</label>
            <div className="flex gap-8">
              <input className="form-input input-flex-2" value={form.f1_7_1} onChange={handleChange('f1_7_1')} placeholder="Наименование" />
              <input className="form-input input-flex-1" value={form.f1_7_2} onChange={handleChange('f1_7_2')} placeholder="ИНН" />
            </div>
          </div>
        </div>
      </div>

      {/* Раздел 2 */}
      <div className="section mb-16">
        <div className="section-subtitle">2. Опасные производственные процессы</div>
        <div className="grid-2" style={{ gap: 8 }}>
          {processChecks.map(c => (
            <label key={c.id} className="checkbox-label">
              <input type="checkbox" checked={!!form.processes[c.id]} onChange={() => setForm({ ...form, processes: { ...form.processes, [c.id]: !form.processes[c.id] } })} className="input-sm" />
              {c.label}
            </label>
          ))}
        </div>
      </div>

      {/* Раздел 3 */}
      <div className="section mb-16">
        <div className="section-subtitle">3. Класс опасности ОПО</div>
        <div style={{ display: 'flex', gap: 16 }}>
          {['I', 'II', 'III', 'IV'].map(cls => (
            <label key={cls} className="checkbox-label" style={{ fontSize: 14, fontWeight: form.danger_class === cls ? 700 : 400 }}>
              <input type="radio" name="danger_class" value={cls} checked={form.danger_class === cls} onChange={handleChange('danger_class')} className="input-sm" />
              {cls}
            </label>
          ))}
        </div>
      </div>

      {/* Раздел 4 */}
      <div className="section mb-16">
        <div className="section-subtitle">4. Классификация ОПО</div>
        <div className="grid-2" style={{ gap: 8 }}>
          {classificationChecks.map(c => (
            <label key={c.id} className="checkbox-label">
              <input type="checkbox" checked={!!form.classification[c.id]} onChange={() => setForm({ ...form, classification: { ...form.classification, [c.id]: !form.classification[c.id] } })} className="input-sm" />
              {c.label}
            </label>
          ))}
        </div>
      </div>

      {/* Раздел 5 */}
      <div className="section mb-16">
        <div className="section-subtitle">5. Лицензии</div>
        <div className="grid-2" style={{ gap: 8 }}>
          {licenseChecks.map(c => (
            <label key={c.id} className="checkbox-label">
              <input type="checkbox" checked={!!form.licenses[c.id]} onChange={() => setForm({ ...form, licenses: { ...form.licenses, [c.id]: !form.licenses[c.id] } })} className="input-sm" />
              {c.label}
            </label>
          ))}
        </div>
      </div>

      {/* Раздел 6 — Таблица состава */}
      <div className="section mb-16">
        <div className="section-subtitle">6. Состав ОПО</div>
        <table className="data-table" style={{ fontSize: 13 }}>
          <thead>
            <tr>
              <th style={{ width: 40 }}>№</th>
              <th>Наименование объекта</th>
              <th style={{ width: 100 }}>Опасное кол-во</th>
              <th>Наименование опасного вещества</th>
              <th>Характеристика</th>
              <th>Процесс</th>
              <th style={{ width: 50 }}></th>
            </tr>
          </thead>
          <tbody>
            {form.composition.map((row, i) => (
              <tr key={i}>
                <td style={{ textAlign: 'center' }}>{i + 1}</td>
                <td><input className="form-input input-compact" value={row.name} onChange={e => handleCompositionChange(i, 'name', e.target.value)} /></td>
                <td><input className="form-input input-compact" type="number" value={row.danger} onChange={e => handleCompositionChange(i, 'danger', e.target.value)} /></td>
                <td><input className="form-input input-compact" value={row.substance} onChange={e => handleCompositionChange(i, 'substance', e.target.value)} /></td>
                <td><input className="form-input input-compact" value={row.characteristics} onChange={e => handleCompositionChange(i, 'characteristics', e.target.value)} /></td>
                <td><input className="form-input input-compact" value={row.processes} onChange={e => handleCompositionChange(i, 'processes', e.target.value)} /></td>
                <td><button className="btn btn-ghost btn-sm text-danger" onClick={() => removeCompositionRow(i)}><i className="fas fa-trash"></i></button></td>
              </tr>
            ))}
          </tbody>
        </table>
        <button className="btn btn-primary btn-sm" style={{ marginTop: 8 }} onClick={addCompositionRow}>
          <i className="fas fa-plus"></i> Добавить строку
        </button>
      </div>

      {/* Раздел 7 */}
      <div className="section mb-16">
        <div className="section-subtitle">7. Опасные вещества в радиусе 500 м</div>
        <textarea className="form-input" rows={3} value={form.f7} onChange={handleChange('f7')} placeholder="Перечень опасных веществ на расстоянии менее 500 м от границ ОПО" />
      </div>

      {/* Раздел 8 — Заявитель */}
      <div className="section mb-16">
        <div className="section-subtitle">8. Заявитель</div>
        <div style={{ display: 'flex', gap: 16, marginBottom: 16 }}>
          <label className="checkbox-label" style={{ fontWeight: form.applicant_type === 'legal' ? 700 : 400 }}>
            <input type="radio" name="applicant_type" value="legal" checked={form.applicant_type === 'legal'} onChange={handleChange('applicant_type')} className="input-sm" />
            Юридическое лицо
          </label>
          <label className="checkbox-label" style={{ fontWeight: form.applicant_type === 'individual' ? 700 : 400 }}>
            <input type="radio" name="applicant_type" value="individual" checked={form.applicant_type === 'individual'} onChange={handleChange('applicant_type')} className="input-sm" />
            Индивидуальный предприниматель
          </label>
        </div>

        {form.applicant_type === 'legal' ? (
          <div className="form-grid">
            <div className="form-group full"><label className="form-label">8.1.1. Полное наименование</label><input className="form-input" value={form.f8_1_1} onChange={handleChange('f8_1_1')} /></div>
            <div className="form-group full"><label className="form-label">8.1.2. Сокращённое наименование</label><input className="form-input" value={form.f8_1_2} onChange={handleChange('f8_1_2')} /></div>
            <div className="form-group"><label className="form-label">8.1.3. ИНН</label><input className="form-input" value={form.f8_1_3} onChange={handleChange('f8_1_3')} maxLength={10} /></div>
            <div className="form-group"><label className="form-label">8.1.4. ОГРН</label><input className="form-input" value={form.f8_1_4} onChange={handleChange('f8_1_4')} /></div>
            <div className="form-group full"><label className="form-label">8.1.5. Адрес</label><input className="form-input" value={form.f8_1_5} onChange={handleChange('f8_1_5')} /></div>
            <div className="form-group"><label className="form-label">8.1.6. Должность</label><input className="form-input" value={form.f8_1_6} onChange={handleChange('f8_1_6')} /></div>
            <div className="form-group"><label className="form-label">8.1.7. ФИО</label><input className="form-input" value={form.f8_1_7} onChange={handleChange('f8_1_7')} /></div>
            <div className="form-group"><label className="form-label">8.1.8. Телефон</label><input className="form-input" value={form.f8_1_8} onChange={handleChange('f8_1_8')} /></div>
            <div className="form-group"><label className="form-label">8.1.9. Email</label><input className="form-input" value={form.f8_1_9} onChange={handleChange('f8_1_9')} /></div>
          </div>
        ) : (
          <div className="form-grid">
            <div className="form-group full"><label className="form-label">8.2.1. ФИО ИП</label><input className="form-input" value={form.f8_2_1} onChange={handleChange('f8_2_1')} /></div>
            <div className="form-group"><label className="form-label">8.2.2. ИНН</label><input className="form-input" value={form.f8_2_2} onChange={handleChange('f8_2_2')} maxLength={12} /></div>
            <div className="form-group"><label className="form-label">8.2.3. ОГРНИП</label><input className="form-input" value={form.f8_2_3} onChange={handleChange('f8_2_3')} /></div>
            <div className="form-group full"><label className="form-label">8.2.4. Адрес</label><input className="form-input" value={form.f8_2_4} onChange={handleChange('f8_2_4')} /></div>
            <div className="form-group"><label className="form-label">8.2.5. Телефон</label><input className="form-input" value={form.f8_2_5} onChange={handleChange('f8_2_5')} /></div>
            <div className="form-group"><label className="form-label">8.2.6. Email</label><input className="form-input" value={form.f8_2_6} onChange={handleChange('f8_2_6')} /></div>
          </div>
        )}
      </div>

      {/* Раздел 9 */}
      <div className="section mb-16">
        <div className="section-subtitle">9. Регистрационный номер</div>
        <div className="form-grid">
          <div className="form-group"><label className="form-label">9.1. Регистрационный номер</label><input className="form-input" value={form.f9_1} onChange={handleChange('f9_1')} /></div>
          <div className="form-group"><label className="form-label">9.2. Временный номер</label><input className="form-input" value={form.f9_2} onChange={handleChange('f9_2')} /></div>
          <div className="form-group"><label className="form-label">9.3. Дата регистрации</label><input className="form-input" type="date" value={form.f9_3} onChange={handleChange('f9_3')} /></div>
          <div className="form-group"><label className="form-label">9.4. Дата изменений</label><input className="form-input" type="date" value={form.f9_4} onChange={handleChange('f9_4')} /></div>
          <div className="form-group full"><label className="form-label">9.5. Наименование органа</label><input className="form-input" value={form.f9_5} onChange={handleChange('f9_5')} /></div>
          <div className="form-group"><label className="form-label">9.6. Должность</label><input className="form-input" value={form.f9_6} onChange={handleChange('f9_6')} /></div>
          <div className="form-group"><label className="form-label">9.7. ФИО</label><input className="form-input" value={form.f9_7} onChange={handleChange('f9_7')} /></div>
        </div>
      </div>

      {/* Подпись */}
      <div className="section mb-16">
        <div className="section-subtitle">Подпись</div>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div className="form-group">
            <label className="form-label">Должность</label>
            <input className="form-input" value={form.signDolj} onChange={handleChange('signDolj')} style={{ width: 200 }} />
          </div>
          <div className="form-group">
            <label className="form-label">Подпись</label>
            <input className="form-input" value={form.signPodp} onChange={handleChange('signPodp')} style={{ width: 200 }} />
          </div>
          <div className="form-group">
            <label className="form-label">Дата</label>
            <input className="form-input" type="date" value={form.signDate} onChange={handleChange('signDate')} />
          </div>
          <div className="form-group">
            <label className="form-label">М.П.</label>
            <input className="form-input" value={form.signMp} onChange={handleChange('signMp')} style={{ width: 100 }} />
          </div>
        </div>
      </div>

      {/* Кнопки */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'flex-end', marginBottom: 40 }}>
        <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? <><i className="fas fa-spinner fa-spin"></i> Сохранение...</> : <><i className="fas fa-save"></i> Сохранить</>}
        </button>
        <button className="btn btn-secondary" onClick={() => handleExport('docx')}>
          <i className="fas fa-download"></i> Скачать DOCX
        </button>
        <button className="btn btn-secondary" onClick={() => handleExport('pdf')}>
          <i className="fas fa-file-pdf"></i> Скачать PDF
        </button>
      </div>
    </div>
  );
}
