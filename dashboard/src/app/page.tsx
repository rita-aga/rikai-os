'use client';

import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { EntityCard } from '@/components/entities';
import {
  Search,
  ArrowRight,
  Target,
  Clock,
  Activity,
  Network,
  Users,
  Command,
} from 'lucide-react';
import type { Entity, ActivityItem } from '@/types';

// Mock data - will be replaced with API calls
const mockCurrentFocus = {
  project: 'RikaiOS Dashboard',
  activeTasks: 3,
  description: 'Building the UI dashboard for the Personal Context Operating System',
};

const mockRecentEntities: Entity[] = [
  {
    id: '1',
    type: 'project',
    name: 'RikaiOS Dashboard',
    content: 'UI dashboard for the Personal Context Operating System',
    metadata: {},
    created_at: '2026-01-07T10:00:00Z',
    updated_at: '2026-01-08T09:30:00Z',
  },
  {
    id: '2',
    type: 'note',
    name: 'Design System Ideas',
    content: 'Japanese minimalism, Ma principle, light and airy',
    metadata: {},
    created_at: '2026-01-07T14:00:00Z',
    updated_at: '2026-01-08T08:15:00Z',
  },
  {
    id: '3',
    type: 'task',
    name: 'Implement search command',
    content: 'Add Cmd+K search palette',
    metadata: {},
    created_at: '2026-01-08T07:00:00Z',
    updated_at: '2026-01-08T07:00:00Z',
  },
  {
    id: '4',
    type: 'topic',
    name: 'React Patterns',
    content: 'Modern React patterns and best practices',
    metadata: {},
    created_at: '2026-01-06T12:00:00Z',
    updated_at: '2026-01-07T16:00:00Z',
  },
];

const mockActivity: ActivityItem[] = [
  {
    id: '1',
    type: 'entity_created',
    entity_type: 'note',
    entity_name: 'Design System Ideas',
    description: 'Created new note',
    timestamp: '2026-01-08T08:15:00Z',
  },
  {
    id: '2',
    type: 'task_completed',
    entity_type: 'task',
    entity_name: 'Set up project structure',
    description: 'Completed task',
    timestamp: '2026-01-08T07:30:00Z',
  },
  {
    id: '3',
    type: 'document_synced',
    description: 'Synced 5 documents from Git',
    timestamp: '2026-01-08T06:00:00Z',
  },
  {
    id: '4',
    type: 'entity_updated',
    entity_type: 'project',
    entity_name: 'RikaiOS Dashboard',
    description: 'Updated project',
    timestamp: '2026-01-07T18:00:00Z',
  },
];

function formatTime(date: string) {
  const now = new Date();
  const then = new Date(date);
  const diff = now.getTime() - then.getTime();
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));

  if (hours < 1) return 'Just now';
  if (hours < 24) return `${hours}h ago`;
  if (days === 1) return 'Yesterday';
  return `${days}d ago`;
}

function getActivityColor(type: ActivityItem['type']) {
  switch (type) {
    case 'entity_created':
      return 'text-entity-note';
    case 'entity_updated':
      return 'text-entity-project';
    case 'task_completed':
      return 'text-accent';
    case 'document_synced':
      return 'text-source-git';
    default:
      return 'text-text-tertiary';
  }
}

export default function DashboardPage() {
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Search Bar - Desktop */}
      <div className="hidden md:block">
        <Button
          variant="secondary"
          className="w-full max-w-2xl mx-auto flex items-center justify-start h-12 px-5"
        >
          <Search className="w-5 h-5 mr-3 text-text-tertiary" />
          <span className="flex-1 text-left text-text-secondary">
            Search across your context...
          </span>
          <kbd className="hidden lg:inline-flex items-center gap-1 rounded-md border border-border bg-background px-2 py-1 font-mono text-xs text-text-tertiary">
            <Command className="w-3 h-3" />K
          </kbd>
        </Button>
      </div>

      {/* Bento Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Now Widget - Spans 2 cols on lg */}
        <Card className="lg:col-span-2">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Target className="w-4 h-4 text-accent" />
                Now
              </CardTitle>
              <Button variant="ghost" size="sm" asChild>
                <Link href="/entities/self" className="text-xs">
                  View focus
                  <ArrowRight className="w-3 h-3 ml-1" />
                </Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="bg-accent-subtle rounded-xl p-5">
              <h3 className="font-semibold text-lg">{mockCurrentFocus.project}</h3>
              <p className="text-sm text-text-secondary mt-1">
                {mockCurrentFocus.description}
              </p>
              <div className="flex items-center gap-4 mt-4 text-sm">
                <span className="flex items-center gap-1.5 text-text-secondary">
                  <Clock className="w-4 h-4 text-entity-task" />
                  {mockCurrentFocus.activeTasks} active tasks
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Activity Feed */}
        <Card className="row-span-2">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Activity</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="space-y-4">
              {mockActivity.map((item) => (
                <div key={item.id} className="flex items-start gap-3">
                  <div className="mt-0.5">
                    <Activity className={`w-4 h-4 ${getActivityColor(item.type)}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm">
                      <span className="text-text-secondary">{item.description}</span>
                      {item.entity_name && (
                        <span className="font-medium"> {item.entity_name}</span>
                      )}
                    </p>
                    <span className="text-xs text-text-tertiary">
                      {formatTime(item.timestamp)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Recent Entities - Spans 2 cols on lg */}
        <Card className="lg:col-span-2">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Recent</CardTitle>
              <Button variant="ghost" size="sm" asChild>
                <Link href="/entities" className="text-xs">
                  View all
                  <ArrowRight className="w-3 h-3 ml-1" />
                </Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {mockRecentEntities.map((entity) => (
                <EntityCard
                  key={entity.id}
                  entity={entity}
                  variant="grid"
                />
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Quick Links */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Quick Access</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 space-y-1">
            <Button variant="ghost" className="w-full justify-start h-10" asChild>
              <Link href="/graph">
                <Network className="w-4 h-4 mr-3 text-accent" />
                Knowledge Graph
              </Link>
            </Button>
            <Button variant="ghost" className="w-full justify-start h-10" asChild>
              <Link href="/hiroba">
                <Users className="w-4 h-4 mr-3 text-entity-person" />
                Hiroba Rooms
              </Link>
            </Button>
            <Button variant="ghost" className="w-full justify-start h-10" asChild>
              <Link href="/entities/tasks">
                <Clock className="w-4 h-4 mr-3 text-entity-task" />
                All Tasks
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
