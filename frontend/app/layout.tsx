import { CopilotKit } from "@copilotkit/react-core"; 
import "@copilotkit/react-ui/v2/styles.css"; 
import './globals.css';

// ...

export default function RootLayout({ children }: {children: React.ReactNode}) {
  return (
    <html lang="en">
      <body>
        <CopilotKit runtimeUrl="/api/copilotkit">
          {children}
        </CopilotKit>
      </body>
    </html>
  );
}