# ==============================================================================
# analysis.R
# Two-Factor Statistical Analysis & Visualization in R (MT2013 - CC09)
# Instructor: Le Xuan Dai
#
# Factor 1: Password Length L on Full Charset (K = 70)
# Factor 2: Charset Complexity K at Fixed Length (L = 4)
# ==============================================================================

# 1. Load Processed Dataset
df <- read.csv("data/processed_experiment_data.csv", stringsAsFactors = FALSE)
cat("=== Total Observations Loaded:", nrow(df), "===\n")

# Check missing values
cat("\nMissing value counts:\n")
print(colSums(is.na(df)))

# 2. Overall Summary Across All Groups
cat("\n======================================================================\n")
cat("Overall Descriptive Statistics by Group\n")
cat("======================================================================\n")
library(stats)
overall_summary <- aggregate(
  cbind(attempts, time_ms) ~ charset_name + length,
  data = df,
  FUN = function(x) c(mean = mean(x), sd = sd(x), median = median(x), iqr = IQR(x))
)
print(overall_summary)

# 3. Axis 1: Length Effect on Full Complexity (K = 70, L in 1..4)
cat("\n======================================================================\n")
cat("Axis 1: Password Length Effect (Full Charset K = 70)\n")
cat("======================================================================\n")
df_axis1 <- subset(df, in_axis1_length == 1)

# One-sample t-tests vs Theoretical E[A] = (70^L + 1) / 2
lengths <- sort(unique(df_axis1$length))
for (L in lengths) {
  sub <- subset(df_axis1, length == L)
  theo_mu <- (70^L + 1) / 2
  t_res <- t.test(sub$attempts, mu = theo_mu, conf.level = 0.95)
  cat(sprintf(
    "L = %d | Theo E[A] = %12.1f | Emp Mean = %12.1f | 95%% CI: [%12.1f, %12.1f] | t = %6.3f, p = %.4f\n",
    L, theo_mu, mean(sub$attempts),
    t_res$conf.int[1], t_res$conf.int[2],
    t_res$statistic, t_res$p.value
  ))
}

# Log-Linear Regression: log10(T) ~ L
model_axis1_log10 <- lm(log10_time_ms ~ length, data = df_axis1)
cat("\n--- OLS Regression: log10(T_ms) ~ Length L ---\n")
print(summary(model_axis1_log10))
cat("95% Confidence Interval for parameters:\n")
print(confint(model_axis1_log10))
cat(sprintf(
  "Theoretical slope log10(70) = %.4f | Empirical slope = %.4f\n",
  log10(70), coef(model_axis1_log10)["length"]
))
cat(sprintf(
  "Implied growth factor 10^b1 = %.2fx per added character (Theoretical = 70x)\n",
  10^(coef(model_axis1_log10)["length"])
))

# 4. Axis 2: Charset Complexity Effect at Fixed Length (L = 4)
cat("\n======================================================================\n")
cat("Axis 2: Charset Complexity Effect at Fixed Length L = 4\n")
cat("======================================================================\n")
df_axis2 <- subset(df, in_axis2_charset == 1)
df_axis2$charset_factor <- factor(
  df_axis2$charset_key,
  levels = c("digits", "lowercase", "alphanumeric", "full"),
  labels = c("Digits (10)", "Lowercase (26)", "Alphanumeric (62)", "Full Special (70)")
)

# One-Way ANOVA on log10(T)
anova_model <- aov(log10_time_ms ~ charset_factor, data = df_axis2)
cat("\n--- One-Way ANOVA Table for log10(Time) across Charset Complexities ---\n")
print(summary(anova_model))

# Tukey HSD Post-hoc Test
cat("\n--- Tukey HSD Post-Hoc Pairwise Comparisons ---\n")
print(TukeyHSD(anova_model))

# Non-parametric Kruskal-Wallis Test
cat("\n--- Kruskal-Wallis Rank Sum Test ---\n")
print(kruskal.test(time_ms ~ charset_factor, data = df_axis2))

# 5. Global Hashing Model: Time (ms) ~ Attempts (A)
cat("\n======================================================================\n")
cat("Global Hashing Speed Model: T_ms ~ Attempts\n")
cat("======================================================================\n")
model_speed <- lm(time_ms ~ attempts, data = df)
print(summary(model_speed))
hash_rate <- 1 / (coef(model_speed)["attempts"] / 1000)
cat(sprintf("Measured CPU Single-Core Hash Rate: %s hashes/sec\n", format(round(hash_rate), big.mark = ",")))

# 6. Diagnostic Plots
pdf("figures/R_diagnostic_plots.pdf", width = 8, height = 6)
par(mfrow = c(2, 2))
plot(model_axis1_log10, main = "Diagnostics: Axis 1 Regression")
dev.off()
cat("\nSaved R diagnostic plots to figures/R_diagnostic_plots.pdf\n")
