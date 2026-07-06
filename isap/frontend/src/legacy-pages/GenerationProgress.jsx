import React, { useState, useEffect, useRef } from 'react';
import { statusLabels } from '../constants';

export default function GenerationProgress({ facilityId, onComplete, onError }) {
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('Подключение...');
  const [section, setSection] = useState('');
  const [sectionNum, setSectionNum] = useState(0);
  const [totalSections, setTotalSections] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [completedSections, setCompletedSections] = useState([]);
  const [status, setStatus] = useState('connecting');
  const [documentId, setDocumentId] = useState(null);
  const [error, setError] = useState(null);
  const timerRef = useRef(null);
  const abortRef = useRef(null);

  useEffect(() => {
    let buffer = '';

    const startGeneration = async () => {
      try {
        const controller = new AbortController();
        abortRef.current = controller;

        const apiKey = localStorage.getItem('isap_api_key') || '';
        const response = await fetch(`/api/v1/pmla/generate/stream?facility_id=${facilityId}`, {
          method: 'POST',
          signal: controller.signal,
          headers: apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {},
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        setStatus('generating');
        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop();

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              const eventType = line.slice(7).trim();
              continue;
            }
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                handleEvent(data);
              } catch (e) {
                console.error('SSE parse error:', e);
              }
            }
          }
        }
      } catch (err) {
        if (err.name !== 'AbortError') {
          setError(err.message);
          setStatus('error');
          onError?.(err);
        }
      }
    };

    const handleEvent = (data) => {
      if (data.percent !== undefined) setProgress(data.percent);
      if (data.message) setMessage(data.message);
      if (data.section) {
        setSection(data.section);
        setSectionNum(data.section_number || 0);
        setTotalSections(data.total_sections || 0);
      }
      if (data.document_id) setDocumentId(data.document_id);
      if (data.step === 'complete') {
        setStatus('complete');
        onComplete?.({ document_id: data.document_id, status: data.status });
      }
      if (data.step === 'section' && data.section_number > 1) {
        setCompletedSections(prev => [...prev, {
          name: sections_list[data.section_number - 2] || `Секция ${data.section_number - 1}`,
          number: data.section_number - 1,
        }]);
      }
    };

    timerRef.current = setInterval(() => {
      setElapsed(prev => prev + 1);
    }, 1000);

    startGeneration();

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (abortRef.current) abortRef.current.abort();
    };
  }, [facilityId]);

  const sections_list = [
    'Общие сведения', 'Анализ опасностей', 'Сценарии аварий',
    'Система оповещения', 'Силы и средства', 'Порядок действий', 'Мероприятия'
  ];

  const formatTime = (s) => {
    if (s < 60) return `${s}с`;
    return `${Math.floor(s / 60)}м ${s % 60}с`;
  };

  const getBarColor = () => {
    if (progress < 30) return 'var(--primary)';
    if (progress < 70) return 'var(--warning)';
    return 'var(--success)';
  };

  return (
    <div style={{ background: 'var(--gray-50)', border: '1px solid var(--gray-200)', borderRadius: 12, padding: 24 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--gray-800)' }}>Генерация ПМЛА</div>
          <div style={{ fontSize: 13, color: 'var(--gray-500)', marginTop: 4 }}>{message}</div>
        </div>
        <div style={{ fontSize: 24 }}>
          {status === 'complete' ? '✅' : status === 'error' ? '❌' : '⚙️'}
        </div>
      </div>

      {/* Progress bar */}
      <div style={{ position: 'relative', height: 36, background: 'var(--gray-200)', borderRadius: 18, overflow: 'hidden', marginBottom: 20 }}>
        <div style={{
          height: '100%',
          width: `${progress}%`,
          background: `linear-gradient(90deg, ${getBarColor()}, ${getBarColor()}dd)`,
          borderRadius: 18,
          transition: 'width 0.5s ease',
          position: 'relative',
          overflow: 'hidden',
        }}>
          <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)',
            animation: status === 'generating' ? 'shimmer 2s infinite' : 'none',
          }} />
        </div>
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          display: 'flex',
          gap: 12,
          alignItems: 'center',
          fontWeight: 600,
          color: 'var(--gray-800)',
          fontSize: 14,
        }}>
          <span>{progress}%</span>
          {status === 'generating' && sectionNum > 0 && (
            <span style={{ fontWeight: 400, fontSize: 12 }}>Секция {sectionNum}/{totalSections}</span>
          )}
          {status === 'complete' && <span style={{ color: 'var(--success)' }}>Готово</span>}
        </div>
      </div>

      {/* Current section */}
      {status === 'generating' && section && (
        <div style={{ padding: '10px 16px', background: 'var(--warning-light)', borderLeft: '3px solid var(--warning)', borderRadius: 4, marginBottom: 16, fontSize: 13 }}>
          <span style={{ color: 'var(--gray-500)' }}>Сейчас: </span>
          <strong>{section}</strong>
        </div>
      )}

      {/* Stats */}
      <div className="grid-3" style={{ gap: 12, marginBottom: 20 }}>
        <div style={{ textAlign: 'center', padding: 12, background: 'var(--gray-100)', borderRadius: 8 }}>
          <div style={{ fontSize: 11, color: 'var(--gray-500)', marginBottom: 4 }}>Прошло</div>
          <div style={{ fontSize: 16, fontWeight: 700 }}>{formatTime(elapsed)}</div>
        </div>
        <div style={{ textAlign: 'center', padding: 12, background: 'var(--gray-100)', borderRadius: 8 }}>
          <div style={{ fontSize: 11, color: 'var(--gray-500)', marginBottom: 4 }}>Секций</div>
          <div style={{ fontSize: 16, fontWeight: 700 }}>{completedSections.length}/{totalSections || '—'}</div>
        </div>
        <div style={{ textAlign: 'center', padding: 12, background: 'var(--gray-100)', borderRadius: 8 }}>
          <div style={{ fontSize: 11, color: 'var(--gray-500)', marginBottom: 4 }}>Статус</div>
          <div style={{ fontSize: 16, fontWeight: 700 }}>{statusLabels[status] || status}</div>
        </div>
      </div>

      {/* Completed sections */}
      {completedSections.length > 0 && (
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--gray-700)', marginBottom: 8 }}>Завершено:</div>
          {completedSections.map((s, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 12px', background: 'var(--success-light)', borderRadius: 6, marginBottom: 4, fontSize: 13 }}>
              <i className="fas fa-check" style={{ color: 'var(--success)', fontSize: 11 }}></i>
              <span>{s.name}</span>
            </div>
          ))}
        </div>
      )}

      {/* Error */}
      {status === 'error' && error && (
        <div className="alert alert-error" style={{ borderLeft: '3px solid var(--danger)', marginTop: 12 }}>
          <strong>Ошибка:</strong> {error}
        </div>
      )}
    </div>
  );
}
