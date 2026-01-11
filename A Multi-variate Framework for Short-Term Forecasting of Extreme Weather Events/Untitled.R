library(rstudioapi)
library(ggplot2)
library(ggExtra)
library(psych)
library(MASS)


# Set working directory to script location
setwd(dirname(getActiveDocumentContext()$path))
par(family = "serif")
data <- read.csv("./Results/rainfall_data.csv")

data <- data[!is.na(data[[16]]) & data[[16]] != 0, ]
selected_cols <- data[, c(10, 12, 14, 16, 18, 20, 22, 24, 26, 28)]

# Remove columns with all NA or constant value
selected_cols <- selected_cols[, sapply(selected_cols, function(col) {
  vals <- col[!is.na(col)]
  length(unique(vals)) > 1
})]

# Remove rows with all NA in remaining columns
selected_cols <- selected_cols[rowSums(is.na(selected_cols)) < ncol(selected_cols), ]


# Calculate correlation matrix
cor_matrix <- cor(selected_cols, method = "spearman", use = "pairwise.complete.obs")

# Find correlations > 0.4 or < -0.4
high_corr <- which(abs(cor_matrix) > 0.4 & abs(cor_matrix) < 1, arr.ind = TRUE)

# Print them nicely
cat("Correlations > 0.4 or < -0.4:\n")
for (i in seq_len(nrow(high_corr))) {
  row <- high_corr[i, "row"]
  col <- high_corr[i, "col"]
  cat(colnames(cor_matrix)[row], "<->", colnames(cor_matrix)[col],
      ":", round(cor_matrix[row, col], 2), "\n")
}

# Now plot
pairs.panels(selected_cols,
             method = "spearman",
             hist.col = "white",
             density = TRUE,
             ellipses = FALSE,
             scale = FALSE,
             lm = TRUE,
             cex.cor = 1.1,
             cex.labels = 1.0,
             cex.axis = 1.8,
             pch = 10,
             col = "red")
pairs.panels(selected_cols,
             method = "spearman",
             hist.col = "white",
             density = TRUE,
             ellipses = FALSE,
             scale = FALSE,
             lm = TRUE,
             cex.cor = 1.1,
             cex.labels = 1.0,
             cex.axis = 1.8,
             pch = 10,
             col = "red")

install.packages("corrplot")  # if not already installed
library(corrplot)

cor_matrix <- cor(selected_cols, method = "spearman", use = "pairwise.complete.obs")

# Plot with colored and highlighted thresholds
corrplot(cor_matrix, method = "color", type = "upper",
         tl.cex = 1.2, number.cex = 1.1,
         addCoef.col = "black", # show correlation values
         col = colorRampPalette(c("blue", "white", "red"))(200),
         tl.col = "black",
         cl.lim = c(-1, 1))
