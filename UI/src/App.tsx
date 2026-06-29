import { HashRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Home } from './pages/Home'
import { Dashboard } from './app/Dashboard'
import { ConsoleTab } from './app/tabs/ConsoleTab'
import { MediaBoardTab } from './app/tabs/MediaBoardTab'
import { CrewTab } from './app/tabs/CrewTab'
import { CasesTab } from './app/tabs/CasesTab'
import { CallsTab } from './app/tabs/CallsTab'
import { SkillsTab } from './app/tabs/SkillsTab'
import { FleetTab } from './app/tabs/FleetTab'
import { AuditTab } from './app/tabs/AuditTab'

export function App() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/app" element={<Dashboard />}>
          <Route index element={<Navigate to="cases" replace />} />
          <Route path="cases" element={<CasesTab />} />
          <Route path="console" element={<ConsoleTab />} />
          <Route path="media" element={<MediaBoardTab />} />
          <Route path="crew" element={<CrewTab />} />
          <Route path="calls" element={<CallsTab />} />
          <Route path="skills" element={<SkillsTab />} />
          <Route path="fleet" element={<FleetTab />} />
          <Route path="audit" element={<AuditTab />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </HashRouter>
  )
}
