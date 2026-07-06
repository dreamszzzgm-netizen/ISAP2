import React, { useState, useEffect } from 'react';
import { pmlaSamplesApi } from '../api';

const facilityTypes = ['', 'Нефтедобыча', 'Нефтепереработка', 'Химическое производство', 'Газораспределение', 'Транспортировка'];
const hazardClasses = ['', 'I', 'II', 'III', 'IV'];

export default function PmlaSamples() {
  const [samples, setSamples] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [filterType, setFilterType] = useState('');
  const [filterClass, setFilterClass] = useState('');
  const [previewSample, setPreviewSample] = useState(null);
  const [previewData, setPreviewData] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const loadSamples = () => {
    setLoading(true);
    const filters = {};
    if (filterType) filters.facility_type = filterType;
    if (filterClass) filters.hazard_class = filterClass;
    pmlaSamplesApi.list(filters)
      .then(setSamples)
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadSamples(); }, [filterType, filterClass]);

  const handleDelete = async (id) => {
    if (!confirm('Удалить образец?')) return;
    try {
      await pmlaSamplesApi.delete(id);
      loadSamples();
    } catch (e) { alert(e.message); }
  };

  const handlePreview = async (sample) => {
    setPreviewSample(sample);
    setPreviewLoading(true);
    setPreviewData(null);
    try {
      const data = await pmlaSamplesApi.preview(sample.id);
      setPreviewData(data);
    } catch (e) {
      setPreviewData({ error: e.message });
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleVerify = async (id, verified) => {
    try {
      await pmlaSamplesApi.verify(id, verified);
      loadSamples();
    } catch (e) { alert(e.message); }
  };

  const handleDownload = async (sample) => {
    try {
      const blob = await pmlaSamplesApi.download(sample.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = sample.file_name;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 10000);
    } catch (e) { alert(e.message); }
  };

  return (
    <div>
      <div className="section">
        <div className="section-header">
          <div>
            <div className="section-title">Образцы ПМЛА</div>
            <div style={{ fontSize: 13, color: 'var(--gray-500)', marginTop: 4 }}>
              Загруженные шаблоны для референса при генерации
            </div>
          </div>
          <div className="section-actions">
            <span style={{ fontSize: 13, color: 'var(--gray-500)', marginRight: 12 }}>Всего: {samples.length}</span>
            <button className="btn btn-primary btn-sm" onClick={() => setShowForm(true)}>
              <i className="fas fa-upload"></i> Загрузить образец
            </button>
          </div>
        </div>

        <div style={{ padding: '16px 24px', display: 'flex', gap: 16, borderBottom: '1px solid var(--gray-100)' }}>
          <div className="form-group" style={{ maxWidth: 250 }}>
            <select className="form-select" value={filterType} onChange={e => setFilterType(e.target.value)}>
              <option value="">Все типы ОПО</option>
              {facilityTypes.filter(Boolean).map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className="form-group" style={{ maxWidth: 200 }}>
            <select className="form-select" value={filterClass} onChange={e => setFilterClass(e.target.value)}>
              <option value="">Все классы</option>
              {hazardClasses.filter(Boolean).map(c => <option key={c} value={c}>{c} класс</option>)}
            </select>
          </div>
        </div>

        {showForm && <UploadForm onClose={() => setShowForm(false)} onUploaded={() => { setShowForm(false); loadSamples(); }} />}

        {loading ? (
          <div className="loading-center"><div className="spinner"></div></div>
        ) : samples.length === 0 ? (
          <div style={{ padding: 60, textAlign: 'center', color: 'var(--gray-400)' }}>
            <i className="fas fa-file-upload" style={{ fontSize: 48, marginBottom: 16, display: 'block' }}></i>
            <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>Нет загруженных образцов</div>
            <div style={{ fontSize: 13, marginBottom: 16 }}>Загрузите DOCX или PDF файл для использования как референс</div>
            <button className="btn btn-primary" onClick={() => setShowForm(true)}>
              <i className="fas fa-upload"></i> Загрузить первый образец
            </button>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 16, padding: 24 }}>
            {samples.map(sample => (
              <div key={sample.id} style={{ background: 'var(--gray-50)', border: '1px solid var(--gray-200)', borderRadius: 8, padding: 20 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--gray-800)', marginBottom: 4 }}>{sample.title}</div>
                    <div style={{ fontSize: 12, color: 'var(--gray-500)' }}>{sample.file_name}</div>
                  </div>
                  {sample.is_verified === 1 && (
                    <span style={{ background: 'var(--success-light)', color: 'var(--success)', padding: '2px 8px', borderRadius: 12, fontSize: 11, fontWeight: 600 }}>
                      <i className="fas fa-check"></i> Проверен
                    </span>
                  )}
                </div>

                {sample.description && (
                  <div style={{ fontSize: 13, color: 'var(--gray-600)', marginBottom: 12 }}>{sample.description}</div>
                )}

                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16, fontSize: 12, color: 'var(--gray-500)' }}>
                  {sample.facility_type && (
                    <span style={{ background: 'var(--gray-100)', padding: '2px 8px', borderRadius: 4 }}>
                      <i className="fas fa-industry"></i> {sample.facility_type}
                    </span>
                  )}
                  {sample.hazard_class && (
                    <span style={{ background: 'var(--warning-light)', color: 'var(--warning)', padding: '2px 8px', borderRadius: 4 }}>
                      <i className="fas fa-exclamation-triangle"></i> {sample.hazard_class} кл.
                    </span>
                  )}
                  <span style={{ background: 'var(--gray-100)', padding: '2px 8px', borderRadius: 4 }}>
                    <i className="fas fa-file"></i> {sample.file_type.toUpperCase()}
                  </span>
                  <span style={{ background: 'var(--gray-100)', padding: '2px 8px', borderRadius: 4 }}>
                    {(sample.file_size / 1024).toFixed(0)} KB
                  </span>
                  <span style={{ background: 'var(--gray-100)', padding: '2px 8px', borderRadius: 4 }}>
                    <i className="fas fa-eye"></i> {sample.usage_count || 0}
                  </span>
                </div>

                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn btn-primary btn-sm" onClick={() => handlePreview(sample)}>
                    <i className="fas fa-eye"></i> Просмотр
                  </button>
                  <button className="btn btn-secondary btn-sm" onClick={() => handleDownload(sample)}>
                    <i className="fas fa-download"></i> Скачать
                  </button>
                  <button className="btn btn-ghost btn-sm" onClick={() => handleVerify(sample.id, sample.is_verified !== 1)}>
                    <i className={sample.is_verified === 1 ? 'fas fa-times' : 'fas fa-check'}></i>
                    {sample.is_verified === 1 ? 'Снять верификацию' : 'Верифицировать'}
                  </button>
                  <button className="btn btn-ghost btn-sm" style={{ color: 'var(--danger)' }} onClick={() => handleDelete(sample.id)}>
                    <i className="fas fa-trash"></i>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {previewSample && (
          <div className="modal-backdrop" onClick={() => { setPreviewSample(null); setPreviewData(null); }}>
            <div className="modal-content" style={{ maxWidth: 800 }} onClick={e => e.stopPropagation()}>
              <div className="modal-header">
                <div>
                  <div style={{ fontSize: 16, fontWeight: 700 }}>{previewSample.title}</div>
                  <div style={{ fontSize: 12, color: 'var(--gray-500)' }}>{previewSample.file_name}</div>
                </div>
                <button className="btn btn-ghost btn-sm" onClick={() => { setPreviewSample(null); setPreviewData(null); }}>
                  <i className="fas fa-times"></i>
                </button>
              </div>
              <div style={{ padding: 24 }}>
                {previewLoading ? (
                  <div style={{ textAlign: 'center', padding: 40 }}>
                    <div className="spinner" style={{ margin: '0 auto 16px' }}></div>
                    <div style={{ color: 'var(--gray-500)' }}>Загрузка превью...</div>
                  </div>
                ) : previewData?.error ? (
                  <div style={{ textAlign: 'center', padding: 40, color: 'var(--danger)' }}>
                    <i className="fas fa-exclamation-circle" style={{ fontSize: 32, marginBottom: 12 }}></i>
                    <div>{previewData.error}</div>
                  </div>
                ) : previewData?.sections?.length > 0 ? (
                  <div>
                    <div style={{ display: 'flex', gap: 8, marginBottom: 20, fontSize: 12 }}>
                      {previewData.facility_type && <span style={{ background: 'var(--gray-100)', padding: '4px 10px', borderRadius: 4 }}>{previewData.facility_type}</span>}
                      {previewData.hazard_class && <span style={{ background: 'var(--warning-light)', color: 'var(--warning)', padding: '4px 10px', borderRadius: 4 }}>{previewData.hazard_class} кл.</span>}
                      <span style={{ background: 'var(--gray-100)', padding: '4px 10px', borderRadius: 4 }}>{previewData.file_type?.toUpperCase()}</span>
                    </div>
                    {previewData.sections.map((section, i) => (
                      <div key={i} style={{ marginBottom: 20 }}>
                        {section.title && (
                          <h3 style={{ fontSize: 15, fontWeight: 700, color: 'var(--gray-800)', marginBottom: 8, paddingBottom: 6, borderBottom: '1px solid var(--gray-100)' }}>
                            {section.title}
                          </h3>
                        )}
                        {section.content?.map((p, j) => (
                          <p key={j} style={{ fontSize: 13, color: 'var(--gray-700)', lineHeight: 1.6, marginBottom: 4 }}>{p}</p>
                        ))}
                      </div>
                    ))}
                    <div style={{ borderTop: '1px solid var(--gray-200)', paddingTop: 16, marginTop: 20, display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
                      <button className="btn btn-secondary" onClick={() => { setPreviewSample(null); setPreviewData(null); }}>Закрыть</button>
                      <button className="btn btn-primary" onClick={() => { handleDownload(previewSample); setPreviewSample(null); setPreviewData(null); }}>
                        <i className="fas fa-download"></i> Скачать
                      </button>
                    </div>
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: 40, color: 'var(--gray-400)' }}>
                    <div>Содержимое недоступно для просмотра</div>
                    <button className="btn btn-secondary" style={{ marginTop: 12 }} onClick={() => { handleDownload(previewSample); setPreviewSample(null); setPreviewData(null); }}>
                      <i className="fas fa-download"></i> Скачать файл
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function UploadForm({ onClose, onUploaded }) {
  const [file, setFile] = useState(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [facilityType, setFacilityType] = useState('');
  const [hazardClass, setHazardClass] = useState('');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) { setError('Выберите файл'); return; }
    if (!title.trim()) { setError('Введите название'); return; }

    setUploading(true);
    setError('');
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('title', title);
      fd.append('description', description);
      fd.append('facility_type', facilityType);
      fd.append('hazard_class', hazardClass);
      await pmlaSamplesApi.upload(fd);
      onUploaded();
    } catch (e) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div style={{ padding: 24, borderBottom: '1px solid var(--gray-100)', background: 'var(--gray-50)' }}>
      <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: 'var(--gray-700)' }}>Загрузка образца ПМЛА</div>
      {error && <div style={{ padding: '8px 12px', background: 'var(--danger-light)', color: 'var(--danger)', borderRadius: 6, marginBottom: 12, fontSize: 13 }}>{error}</div>}
      <form onSubmit={handleSubmit}>
        <div className="form-grid" style={{ marginBottom: 16 }}>
          <div className="form-group full">
            <label className="form-label">Файл <span className="required">*</span></label>
            <input type="file" accept=".docx,.pdf" onChange={e => setFile(e.target.files[0])} className="form-input" />
            <div style={{ fontSize: 12, color: 'var(--gray-500)', marginTop: 4 }}>DOCX или PDF, макс. 50MB</div>
          </div>
          <div className="form-group full">
            <label className="form-label">Название <span className="required">*</span></label>
            <input className="form-input" value={title} onChange={e => setTitle(e.target.value)} placeholder="ПМЛА для нефтебазы ООО 'Нефть'" />
          </div>
          <div className="form-group full">
            <label className="form-label">Описание</label>
            <textarea className="form-input" rows={2} value={description} onChange={e => setDescription(e.target.value)} placeholder="Краткое описание образца..." style={{ resize: 'vertical' }} />
          </div>
          <div className="form-group">
            <label className="form-label">Тип ОПО</label>
            <select className="form-select" value={facilityType} onChange={e => setFacilityType(e.target.value)}>
              <option value="">Не указан</option>
              {facilityTypes.filter(Boolean).map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Класс опасности</label>
            <select className="form-select" value={hazardClass} onChange={e => setHazardClass(e.target.value)}>
              <option value="">Не указан</option>
              {hazardClasses.filter(Boolean).map(c => <option key={c} value={c}>{c} класс</option>)}
            </select>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-primary btn-sm" type="submit" disabled={uploading}>
            {uploading ? 'Загрузка...' : <><i className="fas fa-upload"></i> Загрузить</>}
          </button>
          <button className="btn btn-secondary btn-sm" type="button" onClick={onClose}>Отмена</button>
        </div>
      </form>
    </div>
  );
}
