import { Play } from "lucide-react";
import type { Dict } from "@/content";
import { type Locale, SITE } from "@/lib/site";

/**
 * The product video. Until SITE.videoUrl is set, the frame shows a real screen of the product as
 * its poster and says the video is coming; set the URL and it plays inline, with controls.
 */
export function VideoFrame({ locale, t }: { locale: Locale; t: Dict["home"]["video"] }) {
  const poster = `/screens/builder-claim-${locale}-dark.webp`;
  return (
    <figure className="flex flex-col gap-4">
      <div className="relative aspect-video overflow-hidden rounded-xl bg-canvas shadow-frame">
        {SITE.videoUrl ? (
          // oxlint-disable-next-line jsx-a11y/media-has-caption -- captions ship with the video file.
          <video
            src={SITE.videoUrl}
            poster={poster}
            controls
            preload="none"
            className="size-full object-cover"
          />
        ) : (
          <>
            {/* oxlint-disable-next-line nextjs/no-img-element -- a static export serves pre-sized WebP files. */}
            <img
              src={poster}
              alt=""
              loading="lazy"
              className="size-full object-cover object-top opacity-60"
            />
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-black/35">
              <span className="flex size-14 items-center justify-center rounded-full bg-white/90 text-black">
                <Play className="ms-0.5 size-6" fill="currentColor" />
              </span>
              <span className="rounded-md bg-black/60 px-3 py-1 text-sm text-white">{t.soon}</span>
            </div>
          </>
        )}
      </div>
      <figcaption className="text-sm text-ink-3">{t.caption}</figcaption>
    </figure>
  );
}
