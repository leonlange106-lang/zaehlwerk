import { Card, Table, Skeleton, Alert, Title, Group, Badge, Text } from '@mantine/core';
import { IconAlertTriangle } from '@tabler/icons-react';
import { useApiData } from '../../api/useApi';
import type { DashboardData } from '../../api/types';
import { fmtValue, fmtDate } from '../../util/format';

// Kompakte Desktop-Tabelle aller Systeme mit ihrem aktuellen Stand. Die
// Einzelablesungs-Erfassung/-Historie je System folgt im nächsten Migrations-
// schritt (Detailansicht).
export function ReadingsView() {
  const { data, loading, error } = useApiData<DashboardData>('/api/dashboard/data?months=24');

  if (loading && !data) return <Skeleton h={320} radius="sm" />;
  if (error) return <Alert color="red" icon={<IconAlertTriangle size={16} />}>{error}</Alert>;

  const systems = data?.systems ?? [];

  return (
    <Card>
      <Group justify="space-between" mb="sm">
        <Title order={5}>Zählerstände</Title>
        <Badge variant="light" color="gray">{systems.length} Systeme</Badge>
      </Group>
      <Table.ScrollContainer minWidth={640}>
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>System</Table.Th>
              <Table.Th>Typ</Table.Th>
              <Table.Th ta="right">Aktueller Stand</Table.Th>
              <Table.Th ta="right">Ø / Tag</Table.Th>
              <Table.Th>Letzte Ablesung</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {systems.map((s) => (
              <Table.Tr key={s.id}>
                <Table.Td>
                  <Group gap={8} wrap="nowrap">
                    <span style={{ width: 10, height: 10, borderRadius: 5, background: s.farbe, display: 'inline-block' }} />
                    <Text size="sm">{s.name}</Text>
                  </Group>
                </Table.Td>
                <Table.Td><Text size="sm" c="dimmed">{s.typ}</Text></Table.Td>
                <Table.Td ta="right">{fmtValue(s.latest, s.einheit)}</Table.Td>
                <Table.Td ta="right">{fmtValue(s.avg_per_day, s.einheit)}</Table.Td>
                <Table.Td>{fmtDate(s.latest_datum)}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
    </Card>
  );
}
