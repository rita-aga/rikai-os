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

function getActivityIcon(type: ActivityItem['type']) {
  switch (type) {
    case 'entity_created':
      return <Activity className="w-4 h-4 text-entity-note" />;
    case 'entity_updated':
      return <Activity className="w-4 h-4 text-entity-project" />;
    case 'task_completed':
      return <Activity className="w-4 h-4 text-entity-task" />;
    case 'document_synced':
      return <Activity className="w-4 h-4 text-source-git" />;
    default:
      return <Activity className="w-4 h-4" />;
  }
}

export default function DashboardPage() {
  return (
    <div className="space-ma-md md:space-ma-lg">
      {/* Search Bar - Desktop */}
      <div className="hidden md:block mb-8">
        <Button
          variant="outline"
          className="w-full max-w-2xl mx-auto flex items-center justify-start h-12 px-4 text-muted-foreground hover:text-foreground"
        >
          <Search className="w-5 h-5 mr-3" />
          <span className="flex-1 text-left">Search across your context...</span>
          <kbd className="hidden lg:inline-flex items-center gap-1 rounded border bg-muted px-2 py-0.5 font-mono text-xs">
            <Command className="w-3 h-3" />K
          </kbd>
        </Button>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Now & Activity */}
        <div className="lg:col-span-2 space-y-6">
          {/* Now Widget */}
          <Card className="border-0 shadow-subtle">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Target className="w-5 h-5 text-primary" />
                  Now
                </CardTitle>
                <Button variant="ghost" size="sm" asChild>
                  <Link href="/entities/self">
                    View focus
                    <ArrowRight className="w-4 h-4 ml-1" />
                  </Link>
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="bg-muted/50 rounded-lg p-4">
                <h3 className="font-medium text-lg">{mockCurrentFocus.project}</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  {mockCurrentFocus.description}
                </p>
                <div className="flex items-center gap-4 mt-4 text-sm">
                  <span className="flex items-center gap-1.5">
                    <Clock className="w-4 h-4 text-entity-task" />
                    {mockCurrentFocus.activeTasks} active tasks
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Recent Entities */}
          <Card className="border-0 shadow-subtle">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">Recent</CardTitle>
                <Button variant="ghost" size="sm" asChild>
                  <Link href="/entities">
                    View all
                    <ArrowRight className="w-4 h-4 ml-1" />
                  </Link>
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {/* Horizontal scroll on mobile, grid on desktop */}
              <div className="flex gap-3 overflow-x-auto pb-2 md:grid md:grid-cols-2 md:overflow-visible scrollbar-hide">
                {mockRecentEntities.map((entity) => (
                  <EntityCard
                    key={entity.id}
                    entity={entity}
                    variant="grid"
                    className="min-w-[200px] md:min-w-0"
                  />
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column - Activity & Quick Links */}
        <div className="space-y-6">
          {/* Activity Feed */}
          <Card className="border-0 shadow-subtle">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">Activity</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {mockActivity.map((item) => (
                  <div key={item.id} className="flex items-start gap-3">
                    <div className="mt-0.5">
                      {getActivityIcon(item.type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm">
                        {item.description}
                        {item.entity_name && (
                          <span className="font-medium"> {item.entity_name}</span>
                        )}
                      </p>
                      <span className="text-xs text-muted-foreground">
                        {formatTime(item.timestamp)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Quick Links */}
          <Card className="border-0 shadow-subtle">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">Quick Access</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button variant="ghost" className="w-full justify-start" asChild>
                <Link href="/graph">
                  <Network className="w-4 h-4 mr-3 text-primary" />
                  Knowledge Graph
                </Link>
              </Button>
              <Button variant="ghost" className="w-full justify-start" asChild>
                <Link href="/hiroba">
                  <Users className="w-4 h-4 mr-3 text-entity-person" />
                  Hiroba Rooms
                </Link>
              </Button>
              <Button variant="ghost" className="w-full justify-start" asChild>
                <Link href="/entities/tasks">
                  <Clock className="w-4 h-4 mr-3 text-entity-task" />
                  All Tasks
                </Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
