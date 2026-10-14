package com.example.template

import org.junit.Assert.assertTrue
import org.junit.Test

/** Proves the unit-test worker can load classes (fails under a non-ASCII build dir). */
class SmokeTest {
    @Test
    fun testWorkerLoadsClasses() {
        assertTrue(true)
    }
}
