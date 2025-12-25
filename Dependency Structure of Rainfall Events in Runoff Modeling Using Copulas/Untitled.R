# ==============================================================================
# 1. SETUP LIBRARIES
# ==============================================================================
if(!require(copula)) install.packages("copula")
library(copula)

# ==============================================================================
# 2. LOAD DATA
# ==============================================================================

# Define your specific path (relative to project root)
# Update the station folder name below to match your experiment run
data_path <- "./data/results/HAMILTON RBG CS - 6153301 -- 20251222_223418 -- ce61/01_input_data/"

# Construct full filename
file_name <- paste0(data_path, "03_rainfall_events_data.csv")

# Read the CSV
# check.names = FALSE preserves spaces/brackets in column names like "Volume (mm)"
df_events <- read.csv(file_name, check.names = FALSE)

# Select only the columns you need
# Converting to matrix is often safer for the 'copula' package
raw_data <- as.matrix(df_events[, c("Volume (mm)", "Duration (hrs)")])

# CHECKPOINT: Ensure no missing values (NAs cause fitting errors)
# Removing rows with any NA
raw_data <- na.omit(raw_data)

print(paste("Loaded data with", nrow(raw_data), "events."))

# ==============================================================================
# 3. PRE-PROCESS: CONVERT TO PSEUDO-OBSERVATIONS
# ==============================================================================
# Copulas deal with dependence structure (ranks), not raw values.
# pobs() transforms raw data (mm, hrs) into uniform [0,1] ranks.
uv <- pobs(raw_data)

# ==============================================================================
# 4. DEFINE FITTING LOGIC
# ==============================================================================

fit_copula_family <- function(data, family_name) {
  
  # Initialize the correct model structure
  if (family_name == "Gaussian") {
    model_spec <- normalCopula(dim = 2)
  } else if (family_name == "t") {
    model_spec <- tCopula(dim = 2)
  } else if (family_name == "Clayton") {
    model_spec <- claytonCopula(dim = 2)
  } else if (family_name == "Gumbel") {
    model_spec <- gumbelCopula(dim = 2)
  } else if (family_name == "Frank") {
    model_spec <- frankCopula(dim = 2)
  }
  
  # Fit using Maximum Pseudo-Likelihood (mpl)
  tryCatch({
    fit_obj <- fitCopula(model_spec, data, method = "mpl")
    
    # Extract Metrics
    aic_val <- AIC(fit_obj)
    bic_val <- BIC(fit_obj)
    log_lik <- logLik(fit_obj)
    
    # Extract Params
    params <- coef(fit_obj)
    
    # Re-create fitted object to calculate Tau and Tail Dep
    if (family_name == "t") {
      # tCopula needs both rho and df
      fitted_model <- tCopula(param = params[1], df = params[2], dim = 2)
      param_str <- sprintf("rho=%.3f, df=%.2f", params[1], params[2])
    } else if (family_name == "Gaussian") {
      fitted_model <- normalCopula(param = params, dim = 2)
      param_str <- sprintf("rho=%.3f", params)
    } else {
      # Archimedean
      if (family_name == "Clayton") fitted_model <- claytonCopula(param=params, dim=2)
      if (family_name == "Gumbel")  fitted_model <- gumbelCopula(param=params, dim=2)
      if (family_name == "Frank")   fitted_model <- frankCopula(param=params, dim=2)
      param_str <- sprintf("theta=%.3f", params)
    }
    
    # Calculate Dependence Measures
    tau_val <- tau(fitted_model)
    
    # --- THE FIX IS HERE ---
    # lambda() returns a vector c(lower=..., upper=...), so we must use brackets []
    tail_dep <- lambda(fitted_model) 
    
    return(data.frame(
      Family = family_name,
      AIC = round(aic_val, 2),
      BIC = round(bic_val, 2),
      LogLik = round(as.numeric(log_lik), 2),
      Kendall_Tau = round(tau_val, 3),
      # Use brackets ["name"] instead of $name
      TailDep_Lower = round(as.numeric(tail_dep["lower"]), 3),
      TailDep_Upper = round(as.numeric(tail_dep["upper"]), 3),
      Parameters = param_str
    ))
    
  }, error = function(e) {
    print(paste("Error fitting", family_name, ":", e$message))
    return(NULL)
  })
}
# ==============================================================================
# 5. RUN FIT AND DISPLAY RESULTS
# ==============================================================================

families <- c("Gaussian", "t", "Clayton", "Gumbel", "Frank")
results_list <- list()

for (fam in families) {
  res <- fit_copula_family(uv, fam)
  if (!is.null(res)) {
    results_list[[fam]] <- res
  }
}

# Combine and Sort
final_df <- do.call(rbind, results_list)
final_df <- final_df[order(final_df$AIC), ]

print("-------------------------------------------------------")
print("          RAINFALL VOLUME vs DURATION FITTING          ")
print("-------------------------------------------------------")
print(final_df, row.names = FALSE)

best_copula <- final_df$Family[1]
print("-------------------------------------------------------")
print(paste("WINNER: The", best_copula, "Copula provides the best fit."))
