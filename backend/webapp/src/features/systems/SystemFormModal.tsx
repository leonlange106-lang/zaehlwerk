import { useEffect, useState } from 'react';
import {
  Modal, Stack, Group, Button, TextInput, Select, ColorInput, NumberInput,
  SimpleGrid, Accordion, Text, Divider, Badge, Alert, Anchor,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import {
  IconHome, IconAntenna, IconWorldBolt, IconPlugConnected, IconCheck, IconX,
} from '@tabler/icons-react';
import { apiPost, apiPatch, ApiError } from '../../api/client';
import type { SystemRead } from '../../api/types';

// Zählertypen mit sinnvoller Standard-Einheit und Icon-Kürzel. Ersetzt das
// frühere freie Textfeld (Vue-Parität wiederhergestellt + Wärmepumpe ergänzt).
export const SYSTEM_TYPES = [
  { value: 'Strom', unit: 'kWh', icon: 'bolt' },
  { value: 'Gas', unit: 'm³', icon: 'flame' },
  { value: 'Wasser', unit: 'm³', icon: 'droplet' },
  { value: 'Wärmepumpe', unit: 'kWh', icon: 'heat' },
  { value: 'PV-Erzeugung', unit: 'kWh', icon: 'sun' },
  { value: 'PV-Einspeisung', unit: 'kWh', icon: 'feed' },
  { value: 'Custom', unit: '', icon: 'gauge' },
] as const;

const INTERVAL_OPTIONS = [
  { value: '', label: 'Globale Vorgabe' },
  { value: 'daily', label: 'Täglich' },
  { value: 'weekly', label: 'Wöchentlich' },
  { value: 'monthly', label: 'Monatlich' },
  { value: 'quarterly', label: 'Quartalsweise' },
  { value: 'yearly', label: 'Jährlich' },
];

const MONTH_OPTIONS = [
  { value: '', label: 'Januar (Kalenderjahr)' },
  ...['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August',
    'September', 'Oktober', 'November', 'Dezember'].map((m, i) => ({ value: String(i + 1), label: m })),
];

type NumOrEmpty = number | '';

interface FormValues {
  name: string; typ: string; einheit: string; farbe: string; icon: string;
  preis: NumOrEmpty; abschlag: NumOrEmpty; abrechnungsmonat: string; ablese_intervall_tage: NumOrEmpty;
  brennwert: NumOrEmpty; zustandszahl: NumOrEmpty; kwp: NumOrEmpty; verguetung_ct: NumOrEmpty;
  ha_entity: string; ha_unit: string;
  mqtt_topic: string; mqtt_path: string; mqtt_interval: string;
  rest_url: string; rest_path: string; rest_interval: string;
}

function num(v: unknown): NumOrEmpty {
  return typeof v === 'number' ? v : v != null && v !== '' && !Number.isNaN(Number(v)) ? Number(v) : '';
}
function str(v: unknown): string {
  return v == null ? '' : String(v);
}

function valuesFromSystem(s?: SystemRead): FormValues {
  const zf = (s?.zusatzfelder ?? {}) as Record<string, unknown>;
  return {
    name: s?.name ?? '', typ: s?.typ ?? 'Strom', einheit: s?.einheit ?? 'kWh',
    farbe: s?.farbe ?? '#0e7c86', icon: s?.icon ?? 'bolt',
    preis: num(zf.preis), abschlag: num(zf.abschlag), abrechnungsmonat: str(zf.abrechnungsmonat),
    ablese_intervall_tage: num(zf.ablese_intervall_tage),
    brennwert: num(zf.brennwert), zustandszahl: num(zf.zustandszahl),
    kwp: num(zf.kwp), verguetung_ct: num(zf.verguetung_ct),
    ha_entity: str(zf.ha_entity), ha_unit: str(zf.ha_unit),
    mqtt_topic: str(zf.mqtt_topic), mqtt_path: str(zf.mqtt_path), mqtt_interval: str(zf.mqtt_interval),
    rest_url: str(zf.rest_url), rest_path: str(zf.rest_path), rest_interval: str(zf.rest_interval),
  };
}

function buildZusatzfelder(v: FormValues, existing: Record<string, unknown>): Record<string, unknown> {
  // Bestehende (unbekannte) Schlüssel bewahren, bekannte gezielt setzen/entfernen.
  const zf: Record<string, unknown> = { ...existing };
  const setNum = (k: string, val: NumOrEmpty) => { if (val === '') delete zf[k]; else zf[k] = Number(val); };
  const setStr = (k: string, val: string) => { const t = val.trim(); if (!t) delete zf[k]; else zf[k] = t; };
  setNum('preis', v.preis); setNum('abschlag', v.abschlag); setNum('ablese_intervall_tage', v.ablese_intervall_tage);
  setStr('abrechnungsmonat', v.abrechnungsmonat);
  setNum('brennwert', v.brennwert); setNum('zustandszahl', v.zustandszahl);
  setNum('kwp', v.kwp); setNum('verguetung_ct', v.verguetung_ct);
  setStr('ha_entity', v.ha_entity); setStr('ha_unit', v.ha_unit);
  setStr('mqtt_topic', v.mqtt_topic); setStr('mqtt_path', v.mqtt_path); setStr('mqtt_interval', v.mqtt_interval);
  setStr('rest_url', v.rest_url); setStr('rest_path', v.rest_path); setStr('rest_interval', v.rest_interval);
  return zf;
}

export function SystemFormModal({
  opened, onClose, onSaved, system,
}: {
  opened: boolean; onClose: () => void; onSaved: () => void; system?: SystemRead;
}) {
  const editing = !!system;
  const [busy, setBusy] = useState(false);
  const form = useForm<FormValues>({
    initialValues: valuesFromSystem(system),
    validate: {
      name: (v) => (v.trim().length < 1 ? 'Name erforderlich' : null),
      einheit: (v) => (v.trim().length < 1 ? 'Einheit erforderlich' : null),
    },
  });

  // Bei Öffnen/Wechsel des Systems die Formularwerte neu setzen.
  useEffect(() => {
    if (opened) form.setValues(valuesFromSystem(system));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [opened, system?.id]);

  function onTypeChange(typ: string) {
    form.setFieldValue('typ', typ);
    const preset = SYSTEM_TYPES.find((t) => t.value === typ);
    // Einheit/Icon nur automatisch setzen, wenn der Nutzer sie nicht schon
    // bewusst gefüllt hat (leer = übernehmen).
    if (preset) {
      if (!form.values.einheit || SYSTEM_TYPES.some((t) => t.unit === form.values.einheit)) {
        if (preset.unit) form.setFieldValue('einheit', preset.unit);
      }
      form.setFieldValue('icon', preset.icon);
    }
  }

  async function submit(values: FormValues) {
    setBusy(true);
    try {
      const zusatzfelder = buildZusatzfelder(values, (system?.zusatzfelder ?? {}) as Record<string, unknown>);
      const body = {
        name: values.name.trim(), typ: values.typ.trim(),
        einheit: values.einheit.trim(), farbe: values.farbe, icon: values.icon,
        zusatzfelder,
      };
      if (editing) await apiPatch(`/api/systems/${system!.id}`, body);
      else await apiPost('/api/systems', body);
      notifications.show({ message: editing ? 'System gespeichert' : 'System angelegt', color: 'teal' });
      onSaved();
    } catch (e) {
      notifications.show({ color: 'red', message: e instanceof ApiError ? e.message : 'Speichern fehlgeschlagen' });
    } finally {
      setBusy(false);
    }
  }

  const typ = form.values.typ.toLowerCase();
  const isGas = typ.includes('gas') || form.values.brennwert !== '' || form.values.zustandszahl !== '';

  return (
    <Modal opened={opened} onClose={onClose} title={editing ? 'System bearbeiten' : 'System anlegen'} size="lg" centered>
      <form onSubmit={form.onSubmit(submit)}>
        <Stack gap="md">
          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm">
            <TextInput label="Name" placeholder="z. B. Strom Hauptzähler" {...form.getInputProps('name')} />
            <Select
              label="Zählertyp" data={SYSTEM_TYPES.map((t) => t.value)}
              value={form.values.typ} onChange={(v) => v && onTypeChange(v)}
              allowDeselect={false} checkIconPosition="right"
            />
            <TextInput label="Einheit" placeholder="kWh, m³ …" {...form.getInputProps('einheit')} />
            <ColorInput label="Farbe" {...form.getInputProps('farbe')} />
          </SimpleGrid>

          {isGas && (
            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm">
              <NumberInput label="Brennwert (kWh/m³)" placeholder="11,0" decimalScale={3} {...form.getInputProps('brennwert')} />
              <NumberInput label="Zustandszahl" placeholder="0,95" decimalScale={4} {...form.getInputProps('zustandszahl')} />
            </SimpleGrid>
          )}
          {form.values.typ === 'PV-Erzeugung' && (
            <NumberInput label="Installierte Leistung (kWp)" decimalScale={2} {...form.getInputProps('kwp')} />
          )}
          {form.values.typ === 'PV-Einspeisung' && (
            <NumberInput label="Einspeisevergütung (ct/kWh)" decimalScale={2} {...form.getInputProps('verguetung_ct')} />
          )}

          <Accordion variant="separated" multiple defaultValue={editing ? bindingSections(form.values) : []}>
            <Accordion.Item value="kosten">
              <Accordion.Control icon={<IconPlugConnected size={18} />}>
                <Text size="sm" fw={600}>Kosten &amp; Fälligkeit</Text>
              </Accordion.Control>
              <Accordion.Panel>
                <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm">
                  <NumberInput label="Ø-Preis €/Einheit" description="Fallback für Kostenschätzung" decimalScale={4} {...form.getInputProps('preis')} />
                  <NumberInput label="Monatl. Abschlag €" description="für Prognose-Warnung" decimalScale={2} {...form.getInputProps('abschlag')} />
                  <Select label="Abrechnungsjahr beginnt im" data={MONTH_OPTIONS} {...form.getInputProps('abrechnungsmonat')} />
                  <NumberInput label="Ablese-Intervall (Tage)" description="für Fälligkeit, optional" {...form.getInputProps('ablese_intervall_tage')} />
                </SimpleGrid>
              </Accordion.Panel>
            </Accordion.Item>

            <Accordion.Item value="ha">
              <Accordion.Control icon={<IconHome size={18} />}>
                <Group gap="xs"><Text size="sm" fw={600}>Home Assistant</Text>{form.values.ha_entity && <Badge size="xs" variant="light" color="teal">aktiv</Badge>}</Group>
              </Accordion.Control>
              <Accordion.Panel>
                <Stack gap="sm">
                  <TextInput label="Entity (Zählerstand)" placeholder="sensor.stromzaehler_total" {...form.getInputProps('ha_entity')} />
                  <Select
                    label="Einheit des HA-Sensors" description="leer = wie von HA gemeldet"
                    data={['', 'Wh', 'kWh', 'MWh', 'L', 'm³']} clearable {...form.getInputProps('ha_unit')}
                  />
                  <BindingTester kind="ha" params={{ entity_id: form.values.ha_entity }} disabled={!form.values.ha_entity.trim()} />
                </Stack>
              </Accordion.Panel>
            </Accordion.Item>

            <Accordion.Item value="mqtt">
              <Accordion.Control icon={<IconAntenna size={18} />}>
                <Group gap="xs"><Text size="sm" fw={600}>MQTT · Tasmota · ESPHome</Text>{form.values.mqtt_topic && <Badge size="xs" variant="light" color="teal">aktiv</Badge>}</Group>
              </Accordion.Control>
              <Accordion.Panel>
                <Stack gap="sm">
                  <Group gap="xs">
                    <Text size="xs" c="dimmed">Vorschlag:</Text>
                    <Anchor size="xs" onClick={() => form.setFieldValue('mqtt_topic', 'tele/GERAET/SENSOR')}>Tasmota</Anchor>
                    <Anchor size="xs" onClick={() => { form.setFieldValue('mqtt_topic', 'NODE/sensor/NAME/state'); form.setFieldValue('mqtt_path', ''); }}>ESPHome</Anchor>
                    <Anchor size="xs" onClick={() => form.setFieldValue('mqtt_path', 'ENERGY.Total')}>OBIS/ENERGY-Pfad</Anchor>
                  </Group>
                  <TextInput label="MQTT-Topic" placeholder="tele/hichi/SENSOR" {...form.getInputProps('mqtt_topic')} />
                  <TextInput label="JSON-Pfad (optional)" placeholder="MT631.Total_in" description="leer = automatische Erkennung" {...form.getInputProps('mqtt_path')} />
                  <Select label="Speicherintervall" data={INTERVAL_OPTIONS} {...form.getInputProps('mqtt_interval')} />
                  <Alert color="gray" variant="light" p="xs">
                    <Text size="xs">MQTT wird vom Broker gepusht – ein Live-Test ist erst nach dem Speichern über die Geräteverwaltung (Admin) möglich.</Text>
                  </Alert>
                </Stack>
              </Accordion.Panel>
            </Accordion.Item>

            <Accordion.Item value="rest">
              <Accordion.Control icon={<IconWorldBolt size={18} />}>
                <Group gap="xs"><Text size="sm" fw={600}>REST / HTTP (ESPHome web_server, Shelly)</Text>{form.values.rest_url && <Badge size="xs" variant="light" color="teal">aktiv</Badge>}</Group>
              </Accordion.Control>
              <Accordion.Panel>
                <Stack gap="sm">
                  <Group gap="xs">
                    <Text size="xs" c="dimmed">Vorschlag:</Text>
                    <Anchor size="xs" onClick={() => form.setFieldValue('rest_url', 'http://GERAET.local/sensor/NAME')}>ESPHome</Anchor>
                    <Anchor size="xs" onClick={() => { form.setFieldValue('rest_url', 'http://GERAET.local/rpc/Switch.GetStatus?id=0'); form.setFieldValue('rest_path', 'aenergy.total'); }}>Shelly</Anchor>
                  </Group>
                  <TextInput label="URL" placeholder="http://192.168.1.50/sensor/strom" {...form.getInputProps('rest_url')} />
                  <TextInput label="JSON-Pfad (optional)" placeholder="sensor.total.value" description="leer = automatische Erkennung" {...form.getInputProps('rest_path')} />
                  <Select label="Speicherintervall" data={INTERVAL_OPTIONS} {...form.getInputProps('rest_interval')} />
                  <BindingTester kind="rest" params={{ url: form.values.rest_url, path: form.values.rest_path }} disabled={!form.values.rest_url.trim()} />
                </Stack>
              </Accordion.Panel>
            </Accordion.Item>
          </Accordion>

          <Divider />
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>Abbrechen</Button>
            <Button type="submit" loading={busy}>{editing ? 'Speichern' : 'Anlegen'}</Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

function bindingSections(v: FormValues): string[] {
  const out: string[] = [];
  if (v.ha_entity) out.push('ha');
  if (v.mqtt_topic) out.push('mqtt');
  if (v.rest_url) out.push('rest');
  return out;
}

// Live-Prüfung einer Anbindung über POST /api/systems/binding/test.
function BindingTester({ kind, params, disabled }: {
  kind: 'ha' | 'rest'; params: Record<string, string>; disabled: boolean;
}) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null);

  async function run() {
    setBusy(true); setResult(null);
    try {
      const r = await apiPost<{ ok: boolean; value: unknown; unit?: string; matched_path?: string; error?: string }>(
        '/api/systems/binding/test', { kind, ...params },
      );
      setResult(r.ok
        ? { ok: true, msg: `Wert: ${r.value}${r.unit ? ` ${r.unit}` : ''}${r.matched_path ? ` · ${r.matched_path}` : ''}` }
        : { ok: false, msg: r.error ?? 'Kein Wert erkannt' });
    } catch (e) {
      setResult({ ok: false, msg: e instanceof ApiError ? e.message : 'Test fehlgeschlagen' });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Group gap="sm">
      <Button size="xs" variant="light" onClick={run} loading={busy} disabled={disabled}>Testen</Button>
      {result && (
        <Group gap={4} c={result.ok ? 'teal' : 'red'}>
          {result.ok ? <IconCheck size={16} /> : <IconX size={16} />}
          <Text size="xs">{result.msg}</Text>
        </Group>
      )}
    </Group>
  );
}
