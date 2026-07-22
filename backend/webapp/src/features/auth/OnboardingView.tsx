import { useEffect, useState } from 'react';
import { Center, Paper, Stack, Title, Text, PasswordInput, Button, Alert, Image, TextInput, Code } from '@mantine/core';
import { IconAlertCircle } from '@tabler/icons-react';
import { apiPost, ApiError } from '../../api/client';
import { useAuth } from '../../auth/AuthContext';

interface TwoFactorSetup {
  secret: string;
  qr_data_uri: string;
}

// Erzwungene Erstanmeldung: Passwort ändern, dann Zwei-Faktor einrichten.
export function OnboardingView() {
  const { user, refresh } = useAuth();
  const [step, setStep] = useState<'password' | 'twofa'>(
    user?.temp_password_active ? 'password' : 'twofa',
  );
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');

  const [setup, setSetup] = useState<TwoFactorSetup | null>(null);
  const [code, setCode] = useState('');

  useEffect(() => {
    if (step === 'twofa' && !setup) {
      apiPost<TwoFactorSetup>('/api/auth/2fa/setup')
        .then(setSetup)
        .catch((e) => setError(e instanceof ApiError ? e.message : 'Fehler bei 2FA-Einrichtung'));
    }
  }, [step, setup]);

  async function changePassword() {
    setError(null);
    if (next !== confirm) { setError('Die Passwörter stimmen nicht überein.'); return; }
    setBusy(true);
    try {
      await apiPost('/api/auth/change-password', { current_password: current, new_password: next });
      setStep('twofa');
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Passwortänderung fehlgeschlagen');
    } finally {
      setBusy(false);
    }
  }

  async function activate() {
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
      <Paper p="xl" w={420} shadow="sm">
        <Stack>
          <div>
            <Title order={3}>Einrichtung</Title>
            <Text c="dimmed" size="sm">
              {step === 'password' ? 'Vergib ein eigenes Passwort' : 'Zwei-Faktor aktivieren'}
            </Text>
          </div>

          {error && <Alert color="red" icon={<IconAlertCircle size={16} />} variant="light">{error}</Alert>}

          {step === 'password' ? (
            <Stack>
              <PasswordInput label="Aktuelles (temporäres) Passwort" value={current} onChange={(e) => setCurrent(e.currentTarget.value)} />
              <PasswordInput label="Neues Passwort" value={next} onChange={(e) => setNext(e.currentTarget.value)} />
              <PasswordInput label="Neues Passwort bestätigen" value={confirm} onChange={(e) => setConfirm(e.currentTarget.value)} />
              <Button loading={busy} disabled={!current || !next || next !== confirm} onClick={() => void changePassword()}>
                Weiter
              </Button>
            </Stack>
          ) : (
            <Stack>
              <Text size="sm">Scanne den QR-Code mit deiner Authenticator-App und gib den Code ein.</Text>
              {setup && <Image src={setup.qr_data_uri} w={200} mx="auto" alt="QR-Code" />}
              {setup && <Code>{setup.secret}</Code>}
              <TextInput label="6-stelliger Code" value={code} onChange={(e) => setCode(e.currentTarget.value)} inputMode="numeric" />
              <Button loading={busy} disabled={!setup || code.length < 6} onClick={() => void activate()}>
                Aktivieren &amp; Fertig
              </Button>
            </Stack>
          )}
        </Stack>
      </Paper>
    </Center>
  );
}
