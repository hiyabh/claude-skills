package com.example.template.ui

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.wear.compose.foundation.lazy.ScalingLazyColumn
import androidx.wear.compose.foundation.lazy.rememberScalingLazyListState
import androidx.wear.compose.material.Chip
import androidx.wear.compose.material.ChipDefaults
import androidx.wear.compose.material.MaterialTheme
import androidx.wear.compose.material.Scaffold
import androidx.wear.compose.material.Text
import androidx.wear.compose.material.TimeText
import com.example.template.R

/** Starter screen: title, a line of text and one primary action. Replace freely. */
@Composable
fun HomeScreen() {
    var taps by remember { mutableIntStateOf(0) }
    val listState = rememberScalingLazyListState()
    Scaffold(timeText = { TimeText() }) {
        ScalingLazyColumn(state = listState) {
            item { CenteredText(stringResource(R.string.home_title), MaterialTheme.typography.title2) }
            item { CenteredText(stringResource(R.string.taps_format, taps)) }
            item {
                Chip(
                    onClick = { taps++ },
                    label = { Text(stringResource(R.string.action_tap)) },
                    colors = ChipDefaults.primaryChipColors(),
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        }
    }
}

@Composable
private fun CenteredText(
    text: String,
    style: androidx.compose.ui.text.TextStyle = MaterialTheme.typography.body1,
) {
    Text(text = text, style = style, textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth())
}
