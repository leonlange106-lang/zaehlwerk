import { useState } from 'react';
import {
  Card, Stack, Group, Text, Badge, Button, Table, Select, Skeleton, ActionIcon,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconRefresh, IconEyeOff, IconEye } from '@tabler/icons-react';
import { useApiData } from '../../api/useApi';
import { apiPost, ApiError } from '../../api/client';
import type { SystemRead } from '../../api/types';

interface MqttMapped { system: string; einheit: string; topic: string; interval_label: string }
interface MqttStatus { enabled: boolean; interval: string; mapped: MqttMapped[]; ignored?: string[] }
interface MqttDevice { device: string; topic: string; last_seen?: string }

function notifyError(e: unknown) {
  notifications.show({ color: 'red', message: e instanceof ApiError ? e.message : 'Fehler' });
}

export function MqttTab() {
  const status = useApiData<MqttStatus>('/api/mqtt/status');
  const devices = useApiData<{ devices: MqttDevice[]; discovery: boolean }>('/api/mqtt/devices');
  const systems = useApiData<SystemRead[]>('/api/systems');
  const [assign, setAssign] = useState<Record<string, string | null>>({});

  function reload() { void status.reload(); void devices.reload(); }

  async function act(path: string, body?: unknown, msg = 'Erledigt') {
    try { await apiPost(path, body); notifications.show({ color: 'teal', message: msg }); reload(); }
    catch (e) { notifyError(e); }
  }

  const sysOptions = (systems.data ?? []).filter((s) => s.aktiv).map((s) => ({ value: s.id, label: s.name }));

  return (
    <Stack gap="lg">
      <Card>
        <Group justify="space-between">
          <Group gap="xs">
            <Text fw={600}>MQTT</Text>
            <Badge variant="light" color={status.data?.enabled ? 'teal' : 'gray'}>
              {status.data?.enabled ? 'aktiv' : 'deaktiviert'}
            </Badge>
          </Group>
          <Group gap="xs">
            <Button size="xs" variant="light" leftSection={<IconRefresh size={14} />} onClick={() => void act('/api/mqtt/restart', undefined, 'Neu gestartet')}>Neu starten</Button>
            <Button size="xs" variant="subtle" color="red" onClick={() => void act('/api/mqtt/devices/forget', undefined, 'Erkannte Geräte verworfen')}>Discovery leeren</Button>
          </Group>
        </Group>
      </Card>

      <Card>
        <Text fw={600} mb="sm">Zugeordnete Systeme</Text>
        {status.loading && !status.data ? <Skeleton h={100} /> : (status.data?.mapped ?? []).length === 0 ? (
          <Text size="sm" c="dimmed">Keine Zuordnungen.</Text>
        ) : (
          <Table>
            <Table.Thead><Table.Tr><Table.Th>System</Table.Th><Table.Th>Topic</Table.Th><Table.Th>Intervall</Table.Th></Table.Tr></Table.Thead>
            <Table.Tbody>
              {(status.data?.mapped ?? []).map((m) => (
                <Table.Tr key={m.topic}>
                  <Table.Td>{m.system}</Table.Td>
                  <Table.Td><Text size="xs" ff="monospace">{m.topic}</Text></Table.Td>
                  <Table.Td>{m.interval_label}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Card>

      <Card>
        <Text fw={600} mb="sm">Erkannte Geräte</Text>
        {devices.loading && !devices.data ? <Skeleton h={100} /> : (devices.data?.devices ?? []).length === 0 ? (
          <Text size="sm" c="dimmed">Keine Geräte erkannt. Aktiviere MQTT und warte auf eingehende Nachrichten.</Text>
        ) : (
          <Table.ScrollContainer minWidth={640}>
            <Table>
              <Table.Thead><Table.Tr><Table.Th>Gerät / Topic</Table.Th><Table.Th>Zuletzt</Table.Th><Table.Th>System zuweisen</Table.Th><Table.Th /></Table.Tr></Table.Thead>
              <Table.Tbody>
                {(devices.data?.devices ?? []).map((d) => (
                  <Table.Tr key={d.device}>
                    <Table.Td><Text size="xs" ff="monospace">{d.topic}</Text></Table.Td>
                    <Table.Td><Text size="xs" c="dimmed">{d.last_seen ?? '–'}</Text></Table.Td>
                    <Table.Td>
                      <Group gap={6}>
                        <Select size="xs" w={160} placeholder="System …" data={sysOptions}
                                value={assign[d.device] ?? null}
                                onChange={(v) => setAssign({ ...assign, [d.device]: v })} />
                        <Button size="compact-xs" disabled={!assign[d.device]}
                                onClick={() => void act('/api/mqtt/assign', { system_id: assign[d.device], topic: d.topic }, 'Zugewiesen')}>
                          Zuweisen
                        </Button>
                      </Group>
                    </Table.Td>
                    <Table.Td ta="right">
                      <ActionIcon variant="subtle" color="gray" onClick={() => void act('/api/mqtt/devices/ignore', { device: d.device }, 'Ignoriert')} aria-label="Ignorieren"><IconEyeOff size={16} /></ActionIcon>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        )}

        {(status.data?.ignored ?? []).length > 0 && (
          <>
            <Text size="xs" c="dimmed" mt="md" mb={4}>Ignorierte Geräte</Text>
            <Group gap="xs" wrap="wrap">
              {(status.data?.ignored ?? []).map((dev) => (
                <Badge key={dev} variant="light" color="gray" pr={3}
                       rightSection={
                         <ActionIcon size="xs" variant="transparent" color="teal" aria-label="Wieder anzeigen"
                                     onClick={() => void act('/api/mqtt/devices/unignore', { device: dev }, 'Wieder sichtbar')}>
                           <IconEye size={12} />
                         </ActionIcon>
                       }>
                  {dev}
                </Badge>
              ))}
            </Group>
          </>
        )}
      </Card>
    </Stack>
  );
}
