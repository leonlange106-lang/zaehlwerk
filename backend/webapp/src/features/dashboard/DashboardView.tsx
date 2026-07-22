import { useMemo, useState } from 'react';
import {
  SimpleGrid, Card, Text, Skeleton, Alert, Stack, Table, Title, Group, Button,
  ActionIcon, Menu, Popover, Select, MultiSelect, TextInput, SegmentedControl, Tooltip,
} from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { notifications } from '@mantine/notifications';
import {
  IconAlertTriangle, IconPencil, IconPlus, IconGripVertical, IconTrash, IconSettings,
  IconDeviceFloppy, IconX, IconRefresh, IconCheck,
} from '@tabler/icons-react';
import {
  DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext, rectSortingStrategy, sortableKeyboardCoordinates, useSortable, arrayMove,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useApiData } from '../../api/useApi';
import { api, ApiError } from '../../api/client';
import type { DashboardData, DashboardLayoutResponse, DashboardTile, TileType } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { fmtValue, fmtDate } from '../../util/format';
import { TileBody, TileCard, TILE_LABELS, TIMEFRAME_LABELS } from './tiles';

const GRID_COLS = 4;
const MULTI_TYPES: TileType[] = ['line_chart', 'pie_chart', 'cost_summary'];

// Kachel-Layout links-nach-rechts packen und daraus x/y ableiten (Backend
// prüft nur x+w <= Spaltenzahl, keine Überlappung; h bleibt erhalten).
function repack(tiles: DashboardTile[]): DashboardTile[] {
  let cx = 0, cy = 0;
  return tiles.map((t) => {
    const w = Math.min(Math.max(t.w, 1), GRID_COLS);
    if (cx + w > GRID_COLS) { cx = 0; cy += 1; }
    const placed = { ...t, w, x: cx, y: cy };
    cx += w;
    return placed;
  });
}

export function DashboardView() {
  const { can } = useAuth();
  const canWrite = can('write');
  const layout = useApiData<DashboardLayoutResponse>('/api/user/dashboard');
  const data = useApiData<DashboardData>('/api/dashboard/data?months=24');
  const wide = useMediaQuery('(min-width: 768px)');
  const cols = wide ? GRID_COLS : 1;

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<DashboardTile[]>([]);
  const [busy, setBusy] = useState(false);

  const tiles = editing ? draft : (layout.data?.tiles ?? []);

  const systemOptions = useMemo(
    () => (data.data?.systems ?? []).map((s) => ({ value: s.id, label: s.name })),
    [data.data],
  );

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  function startEdit() {
    setDraft((layout.data?.tiles ?? []).map((t) => ({ ...t })));
    setEditing(true);
  }
  function cancelEdit() { setEditing(false); setDraft([]); }

  function updateTile(id: string, patch: Partial<DashboardTile>) {
    setDraft((prev) => prev.map((t) => (t.id === id ? { ...t, ...patch } : t)));
  }
  function removeTile(id: string) { setDraft((prev) => prev.filter((t) => t.id !== id)); }
  function addTile(type: TileType) {
    const firstId = data.data?.systems[0]?.id ?? null;
    setDraft((prev) => [...prev, {
      id: `w_${type}_${Date.now().toString(36)}`, type,
      x: 0, y: 0, w: type === 'line_chart' ? 2 : 1, h: type === 'line_chart' || type === 'pie_chart' ? 2 : 1,
      system_id: MULTI_TYPES.includes(type) ? null : firstId,
      system_ids: [], timeframe: '12m', title: null,
    }]);
  }

  function onDragEnd(e: DragEndEvent) {
    const { active, over } = e;
    if (!over || active.id === over.id) return;
    setDraft((prev) => {
      const oldIdx = prev.findIndex((t) => t.id === active.id);
      const newIdx = prev.findIndex((t) => t.id === over.id);
      return arrayMove(prev, oldIdx, newIdx);
    });
  }

  async function save() {
    setBusy(true);
    try {
      const packed = repack(draft);
      await api('/api/user/dashboard', { method: 'PUT', body: JSON.stringify({ tiles: packed }) });
      notifications.show({ message: 'Dashboard gespeichert', color: 'teal', icon: <IconCheck size={16} /> });
      setEditing(false);
      await layout.reload();
    } catch (e) {
      notifications.show({ color: 'red', message: e instanceof ApiError ? e.message : 'Speichern fehlgeschlagen' });
    } finally {
      setBusy(false);
    }
  }

  async function reset() {
    if (!confirm('Dashboard auf die Standardbelegung zurücksetzen?')) return;
    setBusy(true);
    try {
      await api('/api/user/dashboard', { method: 'DELETE' });
      notifications.show({ message: 'Auf Standard zurückgesetzt', color: 'teal' });
      setEditing(false);
      await layout.reload();
    } catch (e) {
      notifications.show({ color: 'red', message: e instanceof ApiError ? e.message : 'Fehler' });
    } finally {
      setBusy(false);
    }
  }

  if ((layout.loading && !layout.data) || (data.loading && !data.data)) {
    return (
      <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
        {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} h={180} radius="sm" />)}
      </SimpleGrid>
    );
  }
  if (layout.error) return <Alert color="red" icon={<IconAlertTriangle size={16} />}>{layout.error}</Alert>;

  const gridStyle: React.CSSProperties = {
    display: 'grid',
    gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))`,
    gridAutoRows: 'minmax(120px, auto)',
    gridAutoFlow: 'dense',
    gap: 'var(--mantine-spacing-md)',
  };

  return (
    <Stack gap="lg">
      <Group justify="space-between">
        <Title order={4}>Dashboard</Title>
        {canWrite && !editing && (
          <Button size="xs" variant="light" leftSection={<IconPencil size={16} />} onClick={startEdit}>
            Bearbeiten
          </Button>
        )}
        {editing && (
          <Group gap="xs">
            <Menu position="bottom-end" withinPortal>
              <Menu.Target>
                <Button size="xs" variant="default" leftSection={<IconPlus size={16} />}>Kachel</Button>
              </Menu.Target>
              <Menu.Dropdown>
                {(Object.keys(TILE_LABELS) as TileType[]).map((t) => (
                  <Menu.Item key={t} onClick={() => addTile(t)}>{TILE_LABELS[t]}</Menu.Item>
                ))}
              </Menu.Dropdown>
            </Menu>
            <Button size="xs" variant="subtle" color="gray" leftSection={<IconRefresh size={16} />} onClick={() => void reset()} disabled={busy}>
              Standard
            </Button>
            <Button size="xs" variant="default" leftSection={<IconX size={16} />} onClick={cancelEdit} disabled={busy}>
              Abbrechen
            </Button>
            <Button size="xs" leftSection={<IconDeviceFloppy size={16} />} onClick={() => void save()} loading={busy}>
              Speichern
            </Button>
          </Group>
        )}
      </Group>

      {tiles.length === 0 ? (
        <Card withBorder><Text c="dimmed" size="sm">Keine Kacheln. {canWrite && 'Über „Bearbeiten" hinzufügen.'}</Text></Card>
      ) : editing ? (
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
          <SortableContext items={draft.map((t) => t.id)} strategy={rectSortingStrategy}>
            <div style={gridStyle}>
              {draft.map((tile) => (
                <SortableTile
                  key={tile.id} tile={tile} data={data.data!} cols={cols}
                  systemOptions={systemOptions}
                  onChange={(patch) => updateTile(tile.id, patch)}
                  onRemove={() => removeTile(tile.id)}
                />
              ))}
            </div>
          </SortableContext>
        </DndContext>
      ) : (
        <div style={gridStyle}>
          {tiles.map((tile) => (
            <div key={tile.id} style={{ gridColumn: `span ${Math.min(tile.w, cols)}`, gridRow: `span ${tile.h}` }}>
              <TileCard title={tile.title || TILE_LABELS[tile.type]}>
                <TileBody tile={tile} data={data.data!} />
              </TileCard>
            </div>
          ))}
        </div>
      )}

      {!editing && data.data?.recent && data.data.recent.length > 0 && (
        <Card>
          <Title order={5} mb="sm">Zuletzt erfasst</Title>
          <Table.ScrollContainer minWidth={420}>
            <Table>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>System</Table.Th>
                  <Table.Th>Datum</Table.Th>
                  <Table.Th ta="right">Wert</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {data.data.recent.map((r) => (
                  <Table.Tr key={r.id}>
                    <Table.Td>{r.system}</Table.Td>
                    <Table.Td>{fmtDate(r.datum)}</Table.Td>
                    <Table.Td ta="right">{fmtValue(r.value, r.einheit)}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        </Card>
      )}
    </Stack>
  );
}

function SortableTile({
  tile, data, cols, systemOptions, onChange, onRemove,
}: {
  tile: DashboardTile; data: DashboardData; cols: number;
  systemOptions: { value: string; label: string }[];
  onChange: (patch: Partial<DashboardTile>) => void; onRemove: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: tile.id });
  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform), transition,
    gridColumn: `span ${Math.min(tile.w, cols)}`, gridRow: `span ${tile.h}`,
    opacity: isDragging ? 0.5 : 1, zIndex: isDragging ? 2 : undefined,
  };
  const multi = MULTI_TYPES.includes(tile.type);

  return (
    <div ref={setNodeRef} style={style}>
      <Card h="100%" withBorder style={{ borderStyle: 'dashed' }}>
        <Group justify="space-between" mb={6} wrap="nowrap">
          <ActionIcon variant="subtle" color="gray" {...attributes} {...listeners} style={{ cursor: 'grab' }} aria-label="Verschieben">
            <IconGripVertical size={16} />
          </ActionIcon>
          <Text size="xs" c="dimmed" style={{ flex: 1 }} truncate>{tile.title || TILE_LABELS[tile.type]}</Text>
          <Group gap={2} wrap="nowrap">
            <TileConfig tile={tile} systemOptions={systemOptions} multi={multi} onChange={onChange} />
            <Tooltip label="Entfernen">
              <ActionIcon variant="subtle" color="red" onClick={onRemove} aria-label="Entfernen"><IconTrash size={16} /></ActionIcon>
            </Tooltip>
          </Group>
        </Group>
        <TileBody tile={tile} data={data} />
      </Card>
    </div>
  );
}

function TileConfig({
  tile, systemOptions, multi, onChange,
}: {
  tile: DashboardTile; systemOptions: { value: string; label: string }[];
  multi: boolean; onChange: (patch: Partial<DashboardTile>) => void;
}) {
  const showTimeframe = tile.type === 'line_chart' || tile.type === 'trend';
  return (
    <Popover position="bottom-end" withinPortal shadow="md" width={280}>
      <Popover.Target>
        <ActionIcon variant="subtle" color="gray" aria-label="Einstellungen"><IconSettings size={16} /></ActionIcon>
      </Popover.Target>
      <Popover.Dropdown>
        <Stack gap="sm">
          <TextInput
            label="Titel" size="xs" placeholder={TILE_LABELS[tile.type]}
            value={tile.title ?? ''} onChange={(e) => onChange({ title: e.currentTarget.value || null })}
          />
          <Select
            label="Kacheltyp" size="xs" allowDeselect={false}
            data={(Object.keys(TILE_LABELS) as TileType[]).map((t) => ({ value: t, label: TILE_LABELS[t] }))}
            value={tile.type} onChange={(v) => v && onChange({ type: v as TileType })}
          />
          {multi ? (
            <MultiSelect
              label="Systeme" size="xs" data={systemOptions} searchable clearable
              placeholder="alle"
              value={tile.system_ids && tile.system_ids.length ? tile.system_ids : tile.system_id ? [tile.system_id] : []}
              onChange={(vals) => onChange({ system_ids: vals, system_id: vals[0] ?? null })}
            />
          ) : (
            <Select
              label="System" size="xs" data={systemOptions} searchable clearable
              value={tile.system_id ?? null} onChange={(v) => onChange({ system_id: v, system_ids: v ? [v] : [] })}
            />
          )}
          {showTimeframe && (
            <Select
              label="Zeitraum" size="xs" allowDeselect={false}
              data={(Object.keys(TIMEFRAME_LABELS) as (keyof typeof TIMEFRAME_LABELS)[])
                .filter((t) => t !== 'custom')
                .map((t) => ({ value: t, label: TIMEFRAME_LABELS[t] }))}
              value={tile.timeframe ?? '12m'} onChange={(v) => v && onChange({ timeframe: v as DashboardTile['timeframe'] })}
            />
          )}
          <div>
            <Text size="xs" mb={4}>Breite</Text>
            <SegmentedControl
              size="xs" fullWidth data={['1', '2', '3', '4']}
              value={String(tile.w)} onChange={(v) => onChange({ w: Number(v) })}
            />
          </div>
          <div>
            <Text size="xs" mb={4}>Höhe</Text>
            <SegmentedControl
              size="xs" fullWidth data={['1', '2', '3']}
              value={String(tile.h)} onChange={(v) => onChange({ h: Number(v) })}
            />
          </div>
        </Stack>
      </Popover.Dropdown>
    </Popover>
  );
}
