export default function ReportDisplay({ report }) {
  return (
    <article className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <h3 className="text-lg font-semibold">AI Scouting Report</h3>
      <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-200">{report}</p>
    </article>
  )
}
