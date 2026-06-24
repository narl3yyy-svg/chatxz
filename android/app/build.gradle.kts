import java.util.Properties
import java.io.FileInputStream

plugins {
    id("com.android.application")
    id("com.chaquo.python")
}

val versionProps = Properties().apply {
    val file = rootProject.file("../version.properties")
    if (file.exists()) {
        load(FileInputStream(file))
    }
}
val appVersionName = versionProps.getProperty("VERSION_NAME", "0.0.0")
val appVersionCode = versionProps.getProperty("VERSION_CODE", "1").toInt()
// CI release metadata (keep in sync via scripts/bump-version.sh)
val releaseVersionNameForCi = "0.3.73"  // versionName
val releaseVersionCodeForCi = 73  // versionCode

android {
    namespace = "com.chatxz.android"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.chatxz.android"
        minSdk = 26
        targetSdk = 34
        versionCode = appVersionCode
        versionName = appVersionName

        ndk {
            abiFilters += listOf("arm64-v8a")
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

chaquopy {
    defaultConfig {
        version = "16.1.0"
        pip {
            install("rns>=1.3.0")
            install("aiohttp>=3.9.0")
        }
    }
}

dependencies {
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.constraintlayout:constraintlayout:2.2.0")
    implementation("androidx.webkit:webkit:1.12.1")
}
