import { useState } from 'react';
import { Center, Paper, Stack, TextInput, PasswordInput, Button, Title, Text, Alert, PinInput, Group } from '@mantine/core';
import { useForm } from '@mantine/form';
import { IconAlertCircle } from '@tabler/icons-react';
import { apiPost, ApiError } from '../../api/client';
import { useAuth } from '../../auth/AuthContext';

interface LoginResponse {
  status: 'SUCCESS' | 'REQUIRES_2FA' | 'REQUIRES_FIRST_TIME_SETUP';
}

export function LoginView() {
  const { status, refresh } = useAuth();
  const setupMode = !!status?.setup_required;
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [needsCode, setNeedsCode] = useState(false);
  const [code, setCode] = useState('');

  const form = useForm({
    initialValues: { username: '', password: '' },
    validate: {
      username: (v) => (v.trim().length < 1 ? 'Benutzername erforderlich' : null),
      password: (v) => (v.length < 1 ? 'Passwort erforderlich' : null),
    },
  });

  async function submit(values: { username: string; password: string }) {
    setError(null);
    setBusy(true);
    try {
      if (setupMode) {
        await apiPost('/api/auth/setup', values);
        await refresh();
        return;
      }
      const res = await apiPost<LoginResponse>('/api/auth/login', values);
      if (res.status === 'REQUIRES_2FA') {
        setNeedsCode(true);
      } else {
        await refresh();
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Anmeldung fehlgeschlagen');
    } finally {
      setBusy(false);
    }
  }

  async function verifyCode() {
    setError(null);
    setBusy(true);
    try {
      await apiPost('/api/auth/2fa/verify', { code });
      await refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Code ungültig');
    } finally {
      setBusy(false);
    }
  }

  return (
    <Center mih="100vh" p="md">
      <Paper p="xl" w={380} shadow="sm">
        <Stack>
          <div>
            <Title order={3}>Zählwerk</Title>
            <Text c="dimmed" size="sm">
              {setupMode ? 'Ersteinrichtung: Administrator anlegen' : 'Anmeldung'}
            </Text>
          </div>

          {error && (
            <Alert color="red" icon={<IconAlertCircle size={16} />} variant="light">
              {error}
            </Alert>
          )}

          {needsCode ? (
            <Stack>
              <Text size="sm">Gib den 6-stelligen Code aus deiner Authenticator-App ein.</Text>
              <Group justify="center">
                <PinInput length={6} type="number" value={code} onChange={setCode} oneTimeCode />
              </Group>
              <Button loading={busy} disabled={code.length < 6} onClick={() => void verifyCode()}>
                Bestätigen
              </Button>
              <Button variant="subtle" onClick={() => { setNeedsCode(false); setCode(''); }}>
                Abbrechen
              </Button>
            </Stack>
          ) : (
            <form onSubmit={form.onSubmit(submit)}>
              <Stack>
                <TextInput label="Benutzername" autoComplete="username" {...form.getInputProps('username')} />
                <PasswordInput label="Passwort" autoComplete="current-password" {...form.getInputProps('password')} />
                <Button type="submit" loading={busy}>
                  {setupMode ? 'Administrator anlegen' : 'Anmelden'}
                </Button>
              </Stack>
            </form>
          )}
        </Stack>
      </Paper>
    </Center>
  );
}
