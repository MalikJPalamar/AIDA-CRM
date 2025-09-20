# AIDA-CRM UI Playbook

## Design System Guidelines

### When & How to Use shadcn/ui Components

#### Component Selection Matrix

| Use Case | Primary Component | Alternative | Notes |
|----------|------------------|-------------|-------|
| **Data Display** | Table, Card | DataTable with sorting | Use DataTable for >100 rows |
| **Forms** | Form + Input, Select | Combobox for searchable | Always wrap in Form component |
| **Navigation** | Breadcrumb, Tabs | Sidebar for complex flows | Max 7 tabs per group |
| **Feedback** | Alert, Toast | Progress for long operations | Toast for actions, Alert for states |
| **Overlays** | Dialog, Sheet | Popover for contextual | Dialog for critical actions only |

#### Accessibility Requirements

**Contrast Ratios** (WCAG AA):
- Normal text: minimum 4.5:1
- Large text (18px+): minimum 3:1
- Interactive elements: minimum 3:1

**Keyboard Navigation**:
- All interactive elements accessible via Tab
- Escape key closes modals/overlays
- Arrow keys for list navigation
- Enter/Space for activation

#### Performance Guidelines

**Time to Interactive (TTI)**:
- Target: ≤ 200ms
- Use React.lazy() for heavy components
- Implement skeleton loading states
- Defer non-critical JavaScript

**Cumulative Layout Shift (CLS)**:
- Target: < 0.1
- Reserve space for dynamic content
- Use aspect ratios for images
- Avoid inserting content above viewport

### Component Patterns

#### Lead Capture Form
```tsx
import { Form, FormField, Input, Button } from "@/components/ui"

export function LeadCaptureForm() {
  return (
    <Form>
      <FormField name="email" label="Email">
        <Input type="email" placeholder="Enter your email" />
      </FormField>
      <Button type="submit" className="w-full">
        Capture Lead
      </Button>
    </Form>
  )
}
```

#### Deal Pipeline View
```tsx
import { Card, Badge, Progress } from "@/components/ui"

export function DealCard({ deal }) {
  return (
    <Card className="p-4">
      <div className="flex justify-between items-start">
        <h3 className="font-semibold">{deal.title}</h3>
        <Badge variant={deal.stage}>{deal.stage}</Badge>
      </div>
      <Progress value={deal.probability} className="mt-2" />
      <p className="text-sm text-muted-foreground mt-1">
        ${deal.value.toLocaleString()}
      </p>
    </Card>
  )
}
```

#### Analytics Dashboard
```tsx
import { Card, CardHeader, CardContent } from "@/components/ui"

export function MetricCard({ title, value, change, trend }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <h4 className="text-sm font-medium">{title}</h4>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <div className={`text-xs ${trend === 'up' ? 'text-green-600' : 'text-red-600'}`}>
          {change}% from last month
        </div>
      </CardContent>
    </Card>
  )
}
```

### Motion & Animation

#### Predictable Motion Principles
- **Purposeful**: Animations guide user attention
- **Fast**: 150-300ms duration maximum
- **Smooth**: Use CSS transforms over layout changes
- **Reduced**: Respect `prefers-reduced-motion`

#### Common Patterns
```css
/* Hover states */
.interactive-element {
  transition: all 200ms cubic-bezier(0.4, 0, 0.2, 1);
}

/* Loading states */
.skeleton {
  animation: pulse 2s infinite;
}

/* Page transitions */
.page-enter {
  opacity: 0;
  transform: translateY(16px);
}

.page-enter-active {
  opacity: 1;
  transform: translateY(0);
  transition: all 200ms ease-out;
}
```

### Layout Patterns

#### Responsive Grid System
- **Mobile**: Single column, 16px margins
- **Tablet**: 2-3 columns, 24px margins
- **Desktop**: 4+ columns, 32px margins
- **Large**: Max 1200px width, centered

#### Dashboard Layout
```tsx
export function DashboardLayout({ children }) {
  return (
    <div className="min-h-screen bg-neutral-50">
      <header className="bg-white border-b">
        {/* Navigation */}
      </header>
      <div className="flex">
        <aside className="w-64 bg-white border-r">
          {/* Sidebar */}
        </aside>
        <main className="flex-1 p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
```

### Error Handling

#### Error Boundary Pattern
```tsx
import { Alert, AlertDescription } from "@/components/ui"

export function ErrorFallback({ error, resetErrorBoundary }) {
  return (
    <Alert variant="destructive">
      <AlertDescription>
        Something went wrong: {error.message}
        <Button onClick={resetErrorBoundary} variant="outline" size="sm">
          Try again
        </Button>
      </AlertDescription>
    </Alert>
  )
}
```

#### Loading States
```tsx
import { Skeleton } from "@/components/ui"

export function LeadListSkeleton() {
  return (
    <div className="space-y-4">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="flex items-center space-x-4">
          <Skeleton className="h-12 w-12 rounded-full" />
          <div className="space-y-2">
            <Skeleton className="h-4 w-[250px]" />
            <Skeleton className="h-4 w-[200px]" />
          </div>
        </div>
      ))}
    </div>
  )
}
```

### Testing Patterns

#### Component Testing
```tsx
import { render, screen } from "@testing-library/react"
import { LeadCaptureForm } from "./LeadCaptureForm"

test("submits form with email", async () => {
  const onSubmit = jest.fn()
  render(<LeadCaptureForm onSubmit={onSubmit} />)

  await user.type(screen.getByLabelText("Email"), "test@example.com")
  await user.click(screen.getByRole("button", { name: "Capture Lead" }))

  expect(onSubmit).toHaveBeenCalledWith({ email: "test@example.com" })
})
```

This playbook ensures consistent, accessible, and performant UI development across the AIDA-CRM platform.