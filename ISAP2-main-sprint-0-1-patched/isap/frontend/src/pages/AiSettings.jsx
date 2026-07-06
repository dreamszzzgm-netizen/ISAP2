import React, { useEffect, useState } from 'react';
import { aiApi } from '../api';

function StatusBadge({ status }) {
  const ok = status === 'ok';
  return (
    <span className={`badge ${ok ? 'badge-success' : 'badge-danger'}`}>
      {ok ? 'Доступно' : 'Ошибка'}
    </span>
  );
}

function JsonBlock({ data }) {
  return (
    <pre style={{ whiteSpace: 'pre-wrap', overflowX: 'auto', margin: 0 }}>
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

export default function AiSettings() {
  const [config, setConfig] = useState(null);
  const [chatHealth, setChatHealth] = useState(null);
  const [embeddingHealth, setEmbeddingHealth] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const [cfg, chat, emb] = await Promise.all([
        aiApi.config(),
        aiApi.health(),
        aiApi.embeddingsHealth(),
      ]);
      setConfig(cfg);
      setChatHealth(chat);
      setEmbeddingHealth(emb);
    } catch (err) {
      setError(err.message || 'Ошибка проверки AI');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="page-stack">
      <div className="page-header-row">
        <div>
          <h2>AI / LM Studio</h2>
          <p className="muted">
            Диагностика подключения к локальной модели через OpenAI-compatible API.
          </p>
        </div>
        <button className="btn btn-primary" onClick={load} disabled={loading}>
          {loading ? 'Проверка...' : 'Проверить'}
        </button>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      <div className="grid-2">
        <div className="card">
          <div className="card-header-row">
            <h3>Chat LLM</h3>
            {chatHealth && <StatusBadge status={chatHealth.status} />}
          </div>
          <JsonBlock data={chatHealth || { status: 'loading' }} />
        </div>

        <div className="card">
          <div className="card-header-row">
            <h3>Embeddings</h3>
            {embeddingHealth && <StatusBadge status={embeddingHealth.status} />}
          </div>
          <JsonBlock data={embeddingHealth || { status: 'loading' }} />
        </div>
      </div>

      <div className="card">
        <h3>Текущая конфигурация</h3>
        <JsonBlock data={config || { status: 'loading' }} />
      </div>

      <div className="card">
        <h3>Как настроить LM Studio</h3>
        <ol>
          <li>Открой LM Studio и загрузи chat-модель.</li>
          <li>Включи Local Server на порту 1234.</li>
          <li>Для backend в Docker используй <code>http://host.docker.internal:1234/v1</code>.</li>
          <li>Для backend без Docker используй <code>http://localhost:1234/v1</code>.</li>
          <li>Для RAG загрузи embedding-модель и укажи её в <code>LMSTUDIO_EMBEDDING_MODEL</code>.</li>
        </ol>
      </div>
    </div>
  );
}
