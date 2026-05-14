import Image from 'next/image'

export default function FigureSlot({
  src, alt, label, className,
}: {
  src: string
  alt: string
  label?: string
  className?: string
}) {
  return (
    <div className={className}>
      {label && (
        <p className="text-[10px] font-bold uppercase tracking-wider text-gray-300 mb-2">{label}</p>
      )}
      <div className="border border-gray-100 rounded-xl overflow-hidden bg-gray-50">
        <Image
          src={src}
          alt={alt}
          width={900}
          height={500}
          className="w-full h-auto"
          unoptimized
        />
      </div>
    </div>
  )
}
