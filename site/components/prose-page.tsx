import { Container } from "./ui";

/** A short page of plain paragraphs: legal notice, privacy. */
export function ProsePage({ title, body }: { title: string; body: string[] }) {
  return (
    <article className="py-16 md:py-24">
      <Container className="max-w-[760px]">
        <h1 className="text-headline font-semibold text-ink">{title}</h1>
        <div className="mt-8 flex flex-col gap-4 text-[1.0625rem] leading-relaxed text-ink-2">
          {body.map((paragraph) => (
            <p key={paragraph}>{paragraph}</p>
          ))}
        </div>
      </Container>
    </article>
  );
}
