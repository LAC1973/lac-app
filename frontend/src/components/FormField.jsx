export default function FormField({ label, value, onChange, type = 'text', placeholder, required }) {
  return (
    <div>
      <label className="block text-sm font-medium text-dark-600 mb-1">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-4 py-2.5 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50"
        placeholder={placeholder}
        required={required}
        step={type === 'number' ? 'any' : undefined}
      />
    </div>
  )
}
