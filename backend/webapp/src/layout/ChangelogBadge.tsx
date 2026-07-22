import { useState } from 'react';
import { Badge, Modal, Group, Text, Timeline, List, ScrollArea } from '@mantine/core';
import { IconSparkles } from '@tabler/icons-react';
import { useApiData } from '../api/useApi';

interface ChangelogEntry {
  version: string;
  date: string;
  title: string;
  changes: string[];
}
interface ChangelogResponse {
  current: string;
  entries: ChangelogEntry[];
}

// Versionsnummer als klickbares Badge im Header; öffnet den Versionsverlauf.
export function ChangelogBadge() {
  const [open, setOpen] = useState(false);
  const { data } = useApiData<ChangelogResponse>('/api/changelog');
  const current = data?.current;

  return (
    <>
      <Badge
        variant="light" color="teal" size="sm" style={{ cursor: 'pointer' }}
        onClick={() => setOpen(true)}
        title="Versionsverlauf anzeigen"
      >
        v{current ?? '…'}
      </Badge>
      <Modal opened={open} onClose={() => setOpen(false)} title="Versionsverlauf" size="lg" scrollAreaComponent={ScrollArea.Autosize}>
        {!data ? (
          <Text c="dimmed" size="sm">Lädt …</Text>
        ) : (
          <Timeline active={0} bulletSize={18} lineWidth={2}>
            {data.entries.map((e, i) => (
              <Timeline.Item key={e.version} bullet={i === 0 ? <IconSparkles size={12} /> : undefined}>
                <Group gap="xs" mb={4}>
                  <Text fw={600}>v{e.version}</Text>
                  {e.version === current && <Badge size="xs" color="teal" variant="light">aktuell</Badge>}
                  <Text size="xs" c="dimmed">{e.date}</Text>
                </Group>
                <Text size="sm" fw={500} mb={4}>{e.title}</Text>
                <List size="sm" spacing={2}>
                  {e.changes.map((c, j) => <List.Item key={j}>{c}</List.Item>)}
                </List>
              </Timeline.Item>
            ))}
          </Timeline>
        )}
      </Modal>
    </>
  );
}
