import { useCallback, useEffect, useState } from 'react';
import { api, ApiError } from './client';

// Kleiner Lade-Hook (Daten/Ladezustand/Fehler + reload). Bewusst schlank; für
// komplexere Fälle kann später @tanstack/react-query ergänzt werden.
export function useApiData<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (!path) return;
    setLoading(true);
    setError(null);
    try {
      setData(await api<T>(path));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Fehler beim Laden');
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { data, loading, error, reload };
}
