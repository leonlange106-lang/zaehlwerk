import { useMemo, useState } from 'react';
import {
  Card, Group, Text, Table, Badge, Select, Pagination, Skeleton, Button, Stack, Code,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconArrowBackUp } from '@tabler/icons-react';
import { useApiData } from '../../api/useApi';
import { apiPost, ApiError } from '../../api/client';
import type { AuditResponse, AuditFacets } from '../../api/types';

const ACTION_COLOR: Record<string, string> = { INSERT: 'teal', UPDATE: 'blue', DELETE: 'red' };

export function AuditView() {
  const [page, setPage] = useState(1);
  const [action, setAction] = useState<string | null>(null);
  const [tableFilter, setTableFilter] = useState<string | null>(null);
  const facets = useApiData<AuditFacets>('/api/admin/audit/facets');

  const query = useMemo(() => {
    const p = new URLSearchParams({ page: String(page), per_page: '50' });
    if (action) p.set('action', action);
    if (tableFilter) p.set('target_table', tableFilter);
    return p.toString();
  }, [page, action, tableFilter]);

  const audit = useApiData<AuditResponse>(`/api/admin/audit?${query}`);

  async function rollback(id: number) {
    if (!confirm('Diese Änderung rückgängig machen?')) return;
    try {
      await apiPost(`/api/admin/audit/rollback/${id}`);
      notifications.show({ color: 'teal', message: 'Änderung zurückgenommen' });
      void audit.reload();
    } catch (e) { notifications.show({ color: 'red', message: e instanceof ApiError ? e.message : 'Fehler' }); }
  }

  return (
    <Card>
      <Group justify="space-between" mb="sm">
        <Text fw={600}>Änderungsprotokoll</Text>
        <Group gap="xs">
          <Select placeholder="Aktion" clearable size="xs" w={130}
                  data={(facets.data?.actions ?? []).map((a) => ({ value: a, label: a }))}
                  value={action} onChange={(v) => { setAction(v); setPage(1); }} />
          <Select placeholder="Tabelle" clearable size="xs" w={150}
                  data={(facets.data?.tables ?? []).map((t) => ({ value: t, label: t }))}
                  value={tableFilter} onChange={(v) => { setTableFilter(v); setPage(1); }} />
        </Group>
      </Group>

      {audit.loading && !audit.data ? <Skeleton h={300} /> : (
        <Stack gap="sm">
          <Table.ScrollContainer minWidth={720}>
            <Table>
              <Table.Thead><Table.Tr>
                <Table.Th>Zeit</Table.Th><Table.Th>Konto</Table.Th><Table.Th>Aktion</Table.Th>
                <Table.Th>Tabelle</Table.Th><Table.Th>Ziel</Table.Th><Table.Th />
              </Table.Tr></Table.Thead>
              <Table.Tbody>
                {(audit.data?.entries ?? []).map((e) => (
                  <Table.Tr key={e.id}>
                    <Table.Td><Text size="xs" ff="monospace">{e.ts.replace('T', ' ').slice(0, 19)}</Text></Table.Td>
                    <Table.Td><Text size="sm">{e.username ?? 'System'}</Text></Table.Td>
                    <Table.Td><Badge size="xs" variant="light" color={ACTION_COLOR[e.action] ?? 'gray'}>{e.action}</Badge></Table.Td>
                    <Table.Td><Text size="sm" c="dimmed">{e.target_table}</Text></Table.Td>
                    <Table.Td><Code>{e.target_id ?? '–'}</Code></Table.Td>
                    <Table.Td ta="right">
                      <Button size="compact-xs" variant="subtle" leftSection={<IconArrowBackUp size={14} />} onClick={() => void rollback(e.id)}>
                        Rückgängig
                      </Button>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
          <Group justify="space-between">
            <Text size="xs" c="dimmed">{audit.data?.total ?? 0} Einträge</Text>
            <Pagination total={audit.data?.pages ?? 1} value={page} onChange={setPage} size="sm" />
          </Group>
        </Stack>
      )}
    </Card>
  );
}
