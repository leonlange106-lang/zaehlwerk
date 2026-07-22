import { Card, Stack, Title, Text, Badge } from '@mantine/core';

// Übergangs-Platzhalter für Bereiche, deren Migration noch aussteht. Hält die
// Navigation vollständig, während die Views schrittweise portiert werden.
export function Placeholder({ title, note }: { title: string; note: string }) {
  return (
    <Card>
      <Stack gap="xs">
        <Title order={5}>{title}</Title>
        <Badge color="yellow" variant="light" w="fit-content">In Migration</Badge>
        <Text c="dimmed" size="sm">{note}</Text>
      </Stack>
    </Card>
  );
}
