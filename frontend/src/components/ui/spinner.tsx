import { Loader2Icon } from "lucide-react"
import { motion } from "framer-motion"
import { cn } from "@/lib/utils"

interface SpinnerProps {
  className?: string
  size?: "sm" | "md" | "lg"
  variant?: "default" | "dots" | "pulse"
}

const spinnerVariants = {
  default: {
    spin: {
      rotate: 360,
      transition: {
        duration: 1,
        repeat: Infinity,
        ease: "linear"
      }
    }
  },
  dots: {
    animate: {
      scale: [1, 1.2, 1],
      transition: {
        duration: 0.8,
        repeat: Infinity,
        ease: "easeInOut"
      }
    }
  },
  pulse: {
    pulse: {
      scale: [1, 1.05, 1],
      opacity: [1, 0.7, 1],
      transition: {
        duration: 1.5,
        repeat: Infinity,
        ease: "easeInOut"
      }
    }
  }
}

function Spinner({ className, size = "md", variant = "default", ...props }: SpinnerProps & React.ComponentProps<"svg">) {
  const sizeClasses = {
    sm: "w-4 h-4",
    md: "w-6 h-6",
    lg: "w-8 h-8"
  }

  if (variant === "dots") {
    return (
      <div className={cn("flex items-center gap-1", className)} role="status" aria-label="Loading">
        {[0, 1, 2].map((index) => (
          <motion.div
            key={index}
            className={cn(
              "rounded-full bg-cyan-500",
              size === "sm" ? "w-1 h-1" : size === "md" ? "w-2 h-2" : "w-3 h-3"
            )}
            variants={spinnerVariants.dots}
            animate="animate"
            transition={{ delay: index * 0.2 }}
          />
        ))}
      </div>
    )
  }

  if (variant === "pulse") {
    return (
      <motion.div
        className={cn(
          "rounded-full bg-gradient-to-r from-cyan-500 to-blue-500",
          sizeClasses[size],
          className
        )}
        variants={spinnerVariants.pulse}
        animate="pulse"
        role="status"
        aria-label="Loading"
      />
    )
  }

  return (
    <motion.div
      variants={spinnerVariants.default}
      animate="spin"
      role="status"
      aria-label="Loading"
    >
      <Loader2Icon
        className={cn("size-4", sizeClasses[size], className)}
        {...props}
      />
    </motion.div>
  )
}

export { Spinner }
