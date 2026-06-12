import { CopilotChat } from "@copilotkit/react-core/v2"; 

export default function Page() {
  return (
    <main className="min-h-screen  text-zinc-950">
      <section className="mx-auto flex min-h-screen w-full max-w-6xl flex-col gap-6 px-5 py-6 sm:px-8 lg:px-10">
        <header className="flex flex-col gap-3 text-center border-b border-zinc-200/80 pb-5">
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-red-700">
              Oracle Cloud Infrastructure
            </p>
            <h1 className="text-3xl font-semibold tracking-normal text-zinc-950 sm:text-4xl">
              OCI Grok 4.3 + xAI Tools Demo
            </h1>
          </div>
          
        </header>

        <div className="min-h-0 flex-1 overflow-hidden rounded-lg ">
          <CopilotChat />
        </div>
      </section>
    </main>
  );
}
