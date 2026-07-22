import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Card, Table, Skeleton, Alert, Title, Group, Badge, Text, Anchor, Button, Menu,
  ActionIcon, Collapse,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import {
  IconAlertTriangle, IconPlus, IconDots, IconPencil, IconArchive, IconTrash,
  IconArchiveOff, IconChevronDown,
} from '@tabler/icons-react';
import { useApiData } from '../../api/useApi';
import { apiGet, apiPatch, apiDelete, ApiError } from '../../api/client';
import type { DashboardData, SystemRead } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { fmtValue, fmtDate } from '../../util/format';
import { SystemFormModal } from './SystemFormModal';

// Kompakte Desktop-Tabelle aller Systeme mit aktuellem Stand; Klick öffnet die
// Detailansicht. Anlegen/Bearbeiten via gemeinsame Modalmaske, Archivieren und
// Löschen über das Zeilenmenü.
export function ReadingsView() {
  const { can } = useAuth();
  const canWrite = can('write');
  const dash = useApiData<DashboardData>('/api/dashboard/data?months=24');
  const archived = useApiData<SystemRead[]>('/api/systems?include_archived=true');

  const [formOpen, setFormOpen] = useState(false);
  const [editSystem, setEditSystem] = useState<SystemRead | undefined>();
  const [showArchived, setShowArchived] = useState(false);

  const systems = dash.data?.systems ?? [];
  const archivedOnly = (archived.data ?? []).filter((s) => !s.aktiv);

  function reloadAll() {
    void dash.reload();
    void archived.reload();
  }

  function openCreate() {
    setEditSystem(undefined);
    setFormOpen(true);
  }

  async function openEdit(id: string) {
    try {
      const full = await apiGet<SystemRead>(`/api/systems/${id}`);
      setEditSystem(full);
      setFormOpen(true);
    } catch (e) {
      notifications.show({ color: 'red', message: e instanceof ApiError ? e.message : 'Laden fehlgeschlagen' });
    }
  }

  async function setActive(id: string, aktiv: boolean) {
    try {
      await apiPatch(`/api/systems/${id}`, { aktiv });
      notifications.show({ message: aktiv ? 'System reaktiviert' : 'System archiviert', color: 'teal' });
      reloadAll();
    } catch (e) {
      notifications.show({ color: 'red', message: e instanceof ApiError ? e.message : 'Fehler' });
    }
  }

  async function remove(id: string, name: string) {
    if (!confirm(`System „${name}" mit ALLEN Ablesungen und Zählern endgültig löschen?`)) return;
    try {
      await apiDelete(`/api/systems/${id}`);
      notifications.show({ message: 'System gelöscht', color: 'teal' });
      reloadAll();
    } catch (e) {
      notifications.show({ color: 'red', message: e instanceof ApiError ? e.message : 'Löschen fehlgeschlagen' });
    }
  }

  return (
    <Card>
      <Group justify="space-between" mb="sm">
        <Group gap="sm">
          <Title order={5}>Zählerstände</Title>
          <Badge variant="light" color="gray">{systems.length} Systeme</Badge>
        </Group>
        {canWrite && (
          <Button size="xs" leftSection={<IconPlus size={16} />} onClick={openCreate}>
            System anlegen
          </Button>
        )}
      </Group>

      {dash.error && <Alert color="red" icon={<IconAlertTriangle size={16} />}>{dash.error}</Alert>}
      {dash.loading && !dash.data ? (
        <Skeleton h={280} radius="sm" />
      ) : (
        <Table.ScrollContainer minWidth={640}>
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>System</Table.Th>
                <Table.Th>Typ</Table.Th>
                <Table.Th ta="right">Aktueller Stand</Table.Th>
                <Table.Th ta="right">Ø / Tag</Table.Th>
                <Table.Th>Letzte Ablesung</Table.Th>
                {canWrite && <Table.Th />}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {systems.map((s) => (
                <Table.Tr key={s.id}>
                  <Table.Td>
                    <Group gap={8} wrap="nowrap">
                      <span style={{ width: 10, height: 10, borderRadius: 5, background: s.farbe, display: 'inline-block' }} />
                      <Anchor component={Link} to={`/readings/${s.id}`} size="sm">{s.name}</Anchor>
                    </Group>
                  </Table.Td>
                  <Table.Td><Text size="sm" c="dimmed">{s.typ}</Text></Table.Td>
                  <Table.Td ta="right">{fmtValue(s.latest, s.einheit)}</Table.Td>
                  <Table.Td ta="right">{fmtValue(s.avg_per_day, s.einheit)}</Table.Td>
                  <Table.Td>{fmtDate(s.latest_datum)}</Table.Td>
                  {canWrite && (
                    <Table.Td ta="right">
                      <Menu position="bottom-end" withinPortal>
                        <Menu.Target>
                          <ActionIcon variant="subtle" color="gray" aria-label="Aktionen"><IconDots size={16} /></ActionIcon>
                        </Menu.Target>
                        <Menu.Dropdown>
                          <Menu.Item leftSection={<IconPencil size={14} />} onClick={() => void openEdit(s.id)}>Bearbeiten</Menu.Item>
                          <Menu.Item leftSection={<IconArchive size={14} />} onClick={() => void setActive(s.id, false)}>Archivieren</Menu.Item>
                          <Menu.Divider />
                          <Menu.Item color="red" leftSection={<IconTrash size={14} />} onClick={() => void remove(s.id, s.name)}>Löschen …</Menu.Item>
                        </Menu.Dropdown>
                      </Menu>
                    </Table.Td>
                  )}
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}

      {archivedOnly.length > 0 && (
        <>
          <Button
            variant="subtle" size="xs" color="gray" mt="sm"
            leftSection={<IconChevronDown size={14} style={{ transform: showArchived ? 'rotate(180deg)' : undefined, transition: 'transform .15s' }} />}
            onClick={() => setShowArchived((v) => !v)}
          >
            {archivedOnly.length} archivierte {archivedOnly.length === 1 ? 'System' : 'Systeme'}
          </Button>
          <Collapse in={showArchived}>
            <Table mt="xs">
              <Table.Tbody>
                {archivedOnly.map((s) => (
                  <Table.Tr key={s.id}>
                    <Table.Td>
                      <Group gap={8}>
                        <span style={{ width: 10, height: 10, borderRadius: 5, background: s.farbe, display: 'inline-block', opacity: 0.5 }} />
                        <Text size="sm" c="dimmed">{s.name}</Text>
                        <Badge size="xs" variant="light" color="gray">archiviert</Badge>
                      </Group>
                    </Table.Td>
                    <Table.Td><Text size="sm" c="dimmed">{s.typ}</Text></Table.Td>
                    {canWrite && (
                      <Table.Td ta="right">
                        <Group gap={4} justify="flex-end">
                          <ActionIcon variant="subtle" color="teal" aria-label="Reaktivieren" onClick={() => void setActive(s.id, true)}>
                            <IconArchiveOff size={16} />
                          </ActionIcon>
                          <ActionIcon variant="subtle" color="red" aria-label="Löschen" onClick={() => void remove(s.id, s.name)}>
                            <IconTrash size={16} />
                          </ActionIcon>
                        </Group>
                      </Table.Td>
                    )}
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Collapse>
        </>
      )}

      <SystemFormModal
        opened={formOpen}
        system={editSystem}
        onClose={() => setFormOpen(false)}
        onSaved={() => { setFormOpen(false); reloadAll(); }}
      />
    </Card>
  );
}
