# WAIMS Daily Report Runner
# This script renders the daily report and can be scheduled via cron or Task Scheduler

library(rmarkdown)

# Set report date (defaults to today)
report_date <- Sys.Date()

# Render the report
rmarkdown::render(
  input = "report_templates/waims_daily_report.Rmd",
  output_file = sprintf("WAIMS_Daily_%s.html", format(report_date, "%Y%m%d")),
  output_dir = "reports",
  params = list(report_date = report_date),
  envir = new.env(parent = globalenv())
)

cat("\n✅ Report generated successfully!\n")
cat("   Output: reports/WAIMS_Daily_", format(report_date, "%Y%m%d"), ".html\n", sep = "")
