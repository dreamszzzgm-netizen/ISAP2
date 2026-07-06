import { useState, useRef } from 'react';
import { facilitiesWordApi } from '../api';

export default function WordImportButton({ onImport }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  const handleFile = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.name.endsWith('.docx')) {
      setError('Только формат .docx');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError('Файл слишком большой (макс. 10 МБ)');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const result = await facilitiesWordApi.importWord(file);
      if (result.success && result.data) {
        onImport(result.data, result.warnings || []);
      } else {
        setError('Не удалось извлечь данные');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
      <input
        type="file"
        ref={inputRef}
        accept=".docx"
        onChange={handleFile}
        style={{ display: 'none' }}
        disabled={loading}
      />
      <button
        className="btn btn-secondary btn-sm"
        onClick={() => inputRef.current?.click()}
        disabled={loading}
      >
        {loading ? (
          <><i className="fas fa-spinner fa-spin"></i> Загрузка...</>
        ) : (
          <><i className="fas fa-file-word"></i> Загрузить из Word</>
        )}
      </button>
      {error && <span style={{ color: 'var(--danger)', fontSize: 12 }}>{error}</span>}
    </span>
  );
}
