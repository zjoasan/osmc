/*
 *  Copyright (C) 2005-2018 Team Kodi
 *  This file is part of Kodi - https://kodi.tv
 *
 *  SPDX-License-Identifier: GPL-2.0-or-later
 *  See LICENSES/README.md for more information.
 */

#pragma once

#include <stdint.h>
#include <string>

typedef int DisplayMode;
#define DM_WINDOWED     -1
#define DM_FULLSCREEN    0

enum RESOLUTION
{
  RES_INVALID        = -1,
  RES_WINDOW         = 15,
  RES_DESKTOP        = 16,          // Desktop resolution
  RES_CUSTOM         = 16 + 1,      // First additional resolution
};

struct OVERSCAN
{
  int left;
  int top;
  int right;
  int bottom;
public:
  OVERSCAN()
  {
    left = top = right = bottom = 0;
  }
  OVERSCAN(const OVERSCAN& os)
  {
    left = os.left; top = os.top;
    right = os.right; bottom = os.bottom;
  }
  OVERSCAN& operator=(const OVERSCAN&) = default;

  bool operator==(const OVERSCAN& other)
  {
    return left == other.left && right == other.right && top == other.top && bottom == other.bottom;
  }
  bool operator!=(const OVERSCAN& other)
  {
    return left != other.left || right != other.right || top != other.top || bottom != other.bottom;
  }
};

struct EdgeInsets
{
  float left = 0.0f;
  float top = 0.0f;
  float right = 0.0f;
  float bottom = 0.0f;

  EdgeInsets() = default;
  EdgeInsets(float l, float t, float r, float b);
};

struct RESOLUTION_INFO
{
  OVERSCAN Overscan;
  EdgeInsets guiInsets;
  bool bFullScreen;
  int iWidth;
  int iHeight;
  int iBlanking; /**< number of pixels of padding between stereoscopic frames */
  int iScreenWidth;
  int iScreenHeight;
  int iSubtitles;
  uint32_t dwFlags;
  float fPixelRatio;
  float fRefreshRate;
  std::string strMode;
  std::string strOutput;
  std::string strId;
public:
  RESOLUTION_INFO(int width = 1280, int height = 720, float aspect = 0, const std::string &mode = "");
  float DisplayRatio() const;
  RESOLUTION_INFO(const RESOLUTION_INFO& res);
  RESOLUTION_INFO& operator=(const RESOLUTION_INFO&) = default;
};

class CResolutionUtils
{
public:
  static RESOLUTION ChooseBestResolution(float fps, int width, int height, bool is3D);
  static bool HasWhitelist();
  static void PrintWhitelist();

  /*!
   * \brief Get the max allowed resolution, if fullscreen
   * \param width [OUT] Max width resolution
   * \param height [OUT] Max height resolution
   */
  static void GetMaxAllowedResolution(unsigned int& width, unsigned int& height);

protected:
  static void FindResolutionFromWhitelist(float fps, int width, int height, bool is3D, RESOLUTION &resolution);
  static bool FindResolutionFromOverride(float fps, int width, bool is3D, RESOLUTION &resolution, float& weight, bool fallback);
  static float RefreshWeight(float refresh, float fps);
};
