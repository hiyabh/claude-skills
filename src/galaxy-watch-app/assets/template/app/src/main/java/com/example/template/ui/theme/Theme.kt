package com.example.template.ui.theme

import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.wear.compose.material.Colors
import androidx.wear.compose.material.MaterialTheme

/** Functional and minimal: white on black, greys for secondary surfaces. */
private val WatchColors = Colors(
    primary = Color(0xFFE8E8E8),
    primaryVariant = Color(0xFFBDBDBD),
    secondary = Color(0xFF9E9E9E),
    background = Color.Black,
    surface = Color(0xFF1A1A1A),
    error = Color(0xFFFF6E6E),
    onPrimary = Color.Black,
    onSecondary = Color.Black,
    onBackground = Color.White,
    onSurface = Color.White,
    onError = Color.Black,
)

@Composable
fun WatchTheme(content: @Composable () -> Unit) {
    MaterialTheme(colors = WatchColors, content = content)
}
